from pathlib import Path
import tempfile

from mte_app.session import MTESession


def test_session_roundtrip():
    session = MTESession(
        title="Quadratic",
        problem="Verify a quadratic minimum",
        matlab_code="x = 1;",
        python_code="print(1)",
        lean_code="example : True := by trivial",
        lean_verified=True,
    )
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "sample.mte"
        session.save(path)
        loaded = MTESession.load(path)
        assert loaded == session
