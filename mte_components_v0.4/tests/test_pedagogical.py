from mte_app.pedagogical import (
    build_evidence_summary,
    generate_socratic_hint,
    make_attempt,
)


def test_attempt_ids_increment():
    first = make_attempt([], stage="Python", success=False, status="Failed", summary="x")
    second = make_attempt([first.to_dict()], stage="Lean", success=True, status="Verified", summary="ok")
    assert first.attempt_id == 1
    assert second.attempt_id == 2


def test_summary_distinguishes_computation_from_proof():
    matlab = make_attempt([], stage="MATLAB", success=True, status="Completed", summary="ok").to_dict()
    python = make_attempt([matlab], stage="Python", success=True, status="Completed", summary="ok").to_dict()
    lean = make_attempt([matlab, python], stage="Lean", success=False, status="Rejected", summary="unsolved goals").to_dict()
    summary = build_evidence_summary([matlab, python, lean], lean_verified=False)
    assert "not a formal proof" in summary["matlab"]
    assert "not prove it" in summary["overall"]
    assert "Rejected" in summary["lean"]


def test_lean_hint_is_question_not_solution():
    hint = generate_socratic_hint("Lean", "error: unsolved goals\n⊢ 0 ≤ x ^ 2")
    assert "?" in hint
    assert "exact remaining goal" in hint


def test_python_hint_for_name_error():
    hint = generate_socratic_hint("Python", "NameError: name 'f' is not defined")
    assert "undefined" in hint
    assert "?" in hint
