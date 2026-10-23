from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import zipfile

from .session import MTESession


def build_markdown_report(session: MTESession, summary: dict[str, str]) -> str:
    generated = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    lines = [
        "# Mathematical Thinking Engine — Student Submission",
        "",
        f"Generated: {generated}",
        "",
        "## Problem / Conjecture",
        "",
        session.problem or "(not provided)",
        "",
        "## Cross-language evidence summary",
        "",
        f"**MATLAB:** {summary.get('matlab', '')}",
        "",
        f"**Python:** {summary.get('python', '')}",
        "",
        f"**Lean:** {summary.get('lean', '')}",
        "",
        f"**Interpretation:** {summary.get('overall', '')}",
        "",
        "## Student reflection",
        "",
        session.reflection or "(not provided)",
        "",
        "## Attempt timeline",
        "",
        "| # | Time | Stage | Result | Summary |",
        "|---:|---|---|---|---|",
    ]

    if session.attempts:
        for item in session.attempts:
            summary_text = str(item.get("summary", "")).replace("|", "\\|").replace("\n", " ")
            lines.append(
                f"| {item.get('attempt_id', '')} | {item.get('timestamp', '')} | "
                f"{item.get('stage', '')} | {item.get('status', '')} | {summary_text} |"
            )
    else:
        lines.append("| — | — | — | — | No attempts recorded |")

    lines += [
        "",
        "## MATLAB source",
        "",
        "```matlab",
        session.matlab_code,
        "```",
        "",
        "## Python source",
        "",
        "```python",
        session.python_code,
        "```",
        "",
        "## Lean source",
        "",
        "```lean",
        session.lean_code,
        "```",
        "",
        "## Note on evidence",
        "",
        "Successful MATLAB and Python executions provide computational evidence and diagnostics. Formal proof status is determined by Lean for the theorem actually formalised in the Lean source.",
        "",
    ]
    return "\n".join(lines)


def export_submission_package(
    destination: str | Path,
    session: MTESession,
    summary: dict[str, str],
    figure_paths: list[str] | tuple[str, ...] = (),
) -> Path:
    destination = Path(destination)
    if destination.suffix.lower() != ".zip":
        destination = destination.with_suffix(".zip")
    destination.parent.mkdir(parents=True, exist_ok=True)

    session_json = json.dumps(asdict(session), indent=2, ensure_ascii=False)
    attempts_json = json.dumps(session.attempts, indent=2, ensure_ascii=False)
    report = build_markdown_report(session, summary)

    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("session.mte", session_json)
        archive.writestr("report.md", report)
        archive.writestr("attempts.json", attempts_json)
        archive.writestr("reflection.txt", session.reflection or "")
        archive.writestr("problem.txt", session.problem or "")
        archive.writestr("sources/model.m", session.matlab_code or "")
        archive.writestr("sources/conjecture_test.py", session.python_code or "")
        archive.writestr("sources/proof.lean", session.lean_code or "")
        archive.writestr("outputs/matlab.txt", session.matlab_output or "")
        archive.writestr("outputs/python.txt", session.python_output or "")
        archive.writestr("outputs/lean.txt", session.lean_output or "")
        archive.writestr("summary.json", json.dumps(summary, indent=2, ensure_ascii=False))

        for index, raw_path in enumerate(figure_paths, start=1):
            path = Path(raw_path)
            if path.exists() and path.is_file():
                archive.write(path, f"figures/matlab_figure_{index:02d}{path.suffix.lower() or '.png'}")

    return destination
