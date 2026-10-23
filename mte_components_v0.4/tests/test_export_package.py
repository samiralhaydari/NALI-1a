from pathlib import Path
import tempfile
import zipfile

from mte_app.export_package import export_submission_package
from mte_app.session import MTESession


def test_export_contains_learning_trace():
    session = MTESession(
        problem="Show a claim",
        matlab_code="x = 1;",
        python_code="print(1)",
        lean_code="example : True := by trivial",
        lean_verified=True,
        reflection="The proof formalises the claim.",
        attempts=[
            {
                "attempt_id": 1,
                "timestamp": "2026-10-23T12:00:00+08:00",
                "stage": "Lean",
                "success": True,
                "status": "Verified",
                "summary": "Lean accepted the proof.",
            }
        ],
    )
    summary = {
        "matlab": "Not run yet.",
        "python": "Not run yet.",
        "lean": "Verified.",
        "overall": "Lean accepted the formal proof.",
    }
    with tempfile.TemporaryDirectory() as td:
        path = export_submission_package(Path(td) / "submission.zip", session, summary)
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            assert "report.md" in names
            assert "attempts.json" in names
            assert "reflection.txt" in names
            assert "sources/proof.lean" in names
            assert "session.mte" in names
