from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import re
from typing import Iterable


@dataclass(frozen=True)
class AttemptRecord:
    attempt_id: int
    timestamp: str
    stage: str
    success: bool
    status: str
    summary: str
    exit_code: int | None = None
    from_pipeline: bool = False
    code_snapshot: str = ""
    output_excerpt: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AttemptRecord":
        known = {field for field in cls.__dataclass_fields__}
        return cls(**{key: value for key, value in data.items() if key in known})


def make_attempt(
    existing_attempts: Iterable[dict],
    *,
    stage: str,
    success: bool,
    status: str,
    summary: str,
    exit_code: int | None = None,
    from_pipeline: bool = False,
    code_snapshot: str = "",
    output: str = "",
    timestamp: str | None = None,
) -> AttemptRecord:
    existing = list(existing_attempts)
    attempt_id = max((int(item.get("attempt_id", 0)) for item in existing), default=0) + 1
    stamp = timestamp or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    excerpt = "\n".join((output or "").strip().splitlines()[-12:])
    return AttemptRecord(
        attempt_id=attempt_id,
        timestamp=stamp,
        stage=stage,
        success=success,
        status=status,
        summary=summary,
        exit_code=exit_code,
        from_pipeline=from_pipeline,
        code_snapshot=code_snapshot,
        output_excerpt=excerpt,
    )


def latest_attempt(attempts: Iterable[dict], stage: str) -> dict | None:
    target = stage.casefold()
    matching = [item for item in attempts if str(item.get("stage", "")).casefold() == target]
    if not matching:
        return None
    return max(matching, key=lambda item: int(item.get("attempt_id", 0)))


def build_evidence_summary(
    attempts: Iterable[dict],
    lean_verified: bool | None = None,
) -> dict[str, str]:
    attempts = list(attempts)
    matlab = latest_attempt(attempts, "MATLAB")
    python = latest_attempt(attempts, "Python")
    lean = latest_attempt(attempts, "Lean")

    def computational_text(item: dict | None, language: str) -> str:
        if item is None:
            return "Not run yet."
        if item.get("success"):
            return (
                f"{item.get('status', 'Completed')} — {language} executed successfully. "
                "This is computational evidence, not a formal proof."
            )
        return f"{item.get('status', 'Failed')} — {item.get('summary', 'Execution did not complete.')}"

    matlab_text = computational_text(matlab, "MATLAB")
    python_text = computational_text(python, "Python")

    lean_state = lean_verified
    if lean is not None:
        lean_state = bool(lean.get("success"))

    if lean is None and lean_verified is None:
        lean_text = "Not verified yet."
    elif lean_state:
        lean_text = (
            "Verified — Lean accepted the formal statement and proof. "
            "The guarantee applies to the Lean statement as formalised."
        )
    else:
        lean_text = (
            f"Rejected — {lean.get('summary', 'Lean did not accept the proof.') if lean else 'the saved session records a rejected proof.'}"
        )

    matlab_ok = bool(matlab and matlab.get("success"))
    python_ok = bool(python and python.get("success"))

    if matlab_ok and python_ok and lean_state is True:
        overall = (
            "Computational exploration and executable testing completed, and Lean accepted the formal proof. "
            "Before concluding, check that the Lean theorem faithfully represents the original engineering or mathematical problem."
        )
    elif (matlab_ok or python_ok) and lean_state is False:
        overall = (
            "The computational stages may support the conjecture, but they do not prove it. "
            "Lean rejected the formal proof, so the next learning step is to inspect the formal statement, remaining goal, assumptions, and proof strategy."
        )
    elif lean_state is True and not (matlab_ok and python_ok):
        overall = (
            "Lean accepted the formal proof, but one or more computational stages are incomplete. "
            "The proof result stands for the Lean statement; complete the computational stages if they are part of the intended engineering interpretation."
        )
    elif matlab is None and python is None and lean is None and lean_verified is None:
        overall = "No execution evidence has been recorded yet. Begin by framing the problem and exploring it computationally."
    else:
        overall = (
            "The learning cycle is incomplete. Treat successful MATLAB/Python runs as evidence and diagnostics, then use Lean to test the formal proof."
        )

    return {
        "matlab": matlab_text,
        "python": python_text,
        "lean": lean_text,
        "overall": overall,
    }


def generate_socratic_hint(stage: str, output: str, diagnostic: str = "") -> str:
    stage_key = stage.casefold()
    text = f"{output}\n{diagnostic}".strip()
    lower = text.casefold()

    if stage_key == "lean":
        rules = [
            ("unsolved goals", "What is the exact remaining goal? Which hypothesis, lemma, or transformation would reduce that goal without changing the claim?"),
            ("tactic", "What preconditions does the failed tactic require, and does the current goal have that form? Could you first rewrite or simplify the goal?"),
            ("unknown identifier", "Is the name spelled exactly as Lean expects, and is the required definition or theorem imported or inside a namespace you have not opened?"),
            ("type mismatch", "Compare the type Lean expected with the type it inferred. Which expression or assumption is being interpreted differently from your mathematical intention?"),
            ("failed to synthesize", "Which typeclass instance is Lean trying to infer? Have you specified enough type information for the operation or theorem you are using?"),
            ("declaration uses 'sorry'", "Which unfinished step is currently hidden by `sorry`? Can you restate that step as a smaller goal and justify it directly?"),
        ]
        for needle, hint in rules:
            if needle in lower:
                return hint
        if not text:
            return "Before choosing a tactic, can you state the theorem in words and identify the assumptions, target, and one smaller fact that would make the target easier to prove?"
        return "Find the first Lean message that changes the proof state. What does Lean say it has, what does it still need, and which assumption or lemma could bridge that gap?"

    if stage_key == "python":
        rules = [
            ("nameerror", "Which name is undefined at the point of failure? Where should it have been created, imported, or passed into the function?"),
            ("typeerror", "What types are the operands or arguments at the failing line? Which operation assumes a different type?"),
            ("indexerror", "What are the valid index bounds for this sequence, and which loop or calculation produced the out-of-range index?"),
            ("syntaxerror", "Read the line immediately before the syntax marker as well as the marked line. Is a bracket, quote, colon, or indentation level incomplete?"),
            ("zerodivisionerror", "Which expression became zero in the denominator? Is that case excluded by the mathematics, or must the code handle it explicitly?"),
            ("modulenotfounderror", "Is this dependency actually needed for the conjecture test? If so, is it installed in the same Python environment that runs this application?"),
            ("timed out", "Which loop, recursion, or search can grow without a practical bound? What smaller test case would reveal whether the algorithm is making progress?"),
        ]
        for needle, hint in rules:
            if needle in lower:
                return hint
        if not text:
            return "What specific cases would most strongly challenge your conjecture—boundary values, sign changes, zero, or unusually large/small inputs?"
        return "Can you reduce the failing program to the smallest input and line that reproduces the issue? What mathematical assumption does that line rely on?"

    if stage_key == "matlab":
        rules = [
            ("undefined function or variable", "Which variable or function should exist before this line runs? Is its name, workspace scope, or required toolbox consistent with your model?"),
            ("matrix dimensions", "Write down the dimensions of each array in the failing expression. Which multiplication or element-wise operation matches the mathematics you intended?"),
            ("dimensions must agree", "What are the sizes of the two quantities being combined? Should they be scalars, vectors of the same length, or a matrix product?"),
            ("index exceeds", "What is the size of the array at this point, and how is the index generated? Which boundary case makes the index invalid?"),
            ("timed out", "Which simulation, loop, or solver is consuming the time? Can you reduce the range, resolution, or iteration count while preserving the behavior you want to inspect?"),
        ]
        for needle, hint in rules:
            if needle in lower:
                return hint
        if not text:
            return "Which numerical cases would reveal the structure of the problem most clearly? What pattern would you expect before trying to generalise it?"
        return "What is the smallest numerical case that reproduces this MATLAB result or error, and what mathematical relationship should hold in that case?"

    return "What did you expect to happen, what actually happened, and which assumption can you test next without jumping directly to a final answer?"
