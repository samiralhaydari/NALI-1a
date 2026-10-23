from mte_app.lean_diagnostics import parse_lean_diagnostic


def test_success():
    d = parse_lean_diagnostic("", 0)
    assert d.verified is True
    assert d.line is None


def test_error_location():
    d = parse_lean_diagnostic(
        "/tmp/mte_demo.lean:5:3: error: tactic 'linarith' failed\n⊢ 0 ≤ x ^ 2",
        1,
    )
    assert d.verified is False
    assert d.line == 5
    assert d.column == 3
    assert "linarith" in d.summary


def test_warning_location():
    d = parse_lean_diagnostic(
        "/tmp/mte_demo.lean:2:1: warning: declaration uses 'sorry'",
        0,
    )
    assert d.verified is True
    assert d.severity == "warning"
    assert (d.line, d.column) == (2, 1)
