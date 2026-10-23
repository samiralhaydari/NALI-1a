from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class LeanDiagnostic:
    verified: bool
    title: str
    summary: str
    line: int | None = None
    column: int | None = None
    severity: str = "info"
    raw_message: str = ""

    @property
    def location_text(self) -> str:
        if self.line is None:
            return ""
        if self.column is None:
            return f"Line {self.line}"
        return f"Line {self.line}, column {self.column}"


# Typical Lean messages look like:
# /path/file.lean:5:3: error: tactic '...' failed
_LOCATION = re.compile(
    r"(?P<file>[^\n:]+\.lean):(?P<line>\d+):(?P<column>\d+):\s*"
    r"(?P<severity>error|warning|information):\s*(?P<message>.*)",
    re.IGNORECASE,
)


def parse_lean_diagnostic(output: str, exit_code: int) -> LeanDiagnostic:
    clean = (output or "").strip()

    if exit_code == 0:
        warning_match = next(
            (m for m in _LOCATION.finditer(clean) if m.group("severity").lower() == "warning"),
            None,
        )
        if warning_match:
            return LeanDiagnostic(
                verified=True,
                title="✓ PROOF VERIFIED",
                summary="Lean accepted the submission with warning(s).",
                line=int(warning_match.group("line")),
                column=int(warning_match.group("column")),
                severity="warning",
                raw_message=warning_match.group("message").strip(),
            )
        return LeanDiagnostic(
            verified=True,
            title="✓ PROOF VERIFIED",
            summary="Lean accepted the submission. No proof errors were reported.",
            severity="success",
            raw_message=clean,
        )

    error_match = next(
        (m for m in _LOCATION.finditer(clean) if m.group("severity").lower() == "error"),
        None,
    )
    if error_match:
        message = error_match.group("message").strip()
        return LeanDiagnostic(
            verified=False,
            title="✗ PROOF REJECTED",
            summary=message or "Lean rejected the submission.",
            line=int(error_match.group("line")),
            column=int(error_match.group("column")),
            severity="error",
            raw_message=clean,
        )

    first_line = next((line.strip() for line in clean.splitlines() if line.strip()), "")
    return LeanDiagnostic(
        verified=False,
        title="✗ PROOF REJECTED",
        summary=first_line or f"Lean exited with code {exit_code}.",
        severity="error",
        raw_message=clean,
    )
