import unittest

from mte_app.lean_diagnostics import parse_lean_diagnostic


class LeanDiagnosticTests(unittest.TestCase):
    def test_verified_clean(self):
        d = parse_lean_diagnostic("", 0)
        self.assertTrue(d.verified)
        self.assertEqual(d.title, "✓ PROOF VERIFIED")

    def test_error_with_location(self):
        output = "/tmp/mte_abc.lean:5:3: error: tactic 'linarith' failed\n⊢ 0 ≤ x ^ 2"
        d = parse_lean_diagnostic(output, 1)
        self.assertFalse(d.verified)
        self.assertEqual(d.line, 5)
        self.assertEqual(d.column, 3)
        self.assertIn("linarith", d.summary)

    def test_warning_but_verified(self):
        output = "/tmp/mte_abc.lean:2:1: warning: declaration uses 'sorry'"
        d = parse_lean_diagnostic(output, 0)
        self.assertTrue(d.verified)
        self.assertEqual(d.severity, "warning")
        self.assertEqual(d.line, 2)


if __name__ == "__main__":
    unittest.main()
