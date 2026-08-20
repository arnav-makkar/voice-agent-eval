import unittest

from framework.experiments.run_gepa import lint_candidate, lint_deployable_candidate


class GepaCompatibilityTests(unittest.TestCase):
    def test_rejects_unsupported_disposition(self):
        prompt = "payment_ready fptp wrong_number dispute escalation OTP CVV " + "x" * 1000 + " `promise_to_pay`"
        self.assertIn("unsupported disposition token: promise_to_pay", lint_candidate(prompt))

    def test_allows_negated_compatibility_guardrail(self):
        prompt = "payment_ready fptp wrong_number dispute escalation OTP CVV " + "x" * 1000 + "\nNever introduce `promise_to_pay` as a disposition."
        self.assertEqual(lint_candidate(prompt), [])

    def test_accepts_platform_compatible_surface(self):
        prompt = "payment_ready fptp wrong_number dispute escalation OTP CVV " + "x" * 1000
        self.assertEqual(lint_candidate(prompt), [])

    def test_deployable_lint_rejects_frozen_dates(self):
        prompt = "payment_ready fptp wrong_number dispute escalation OTP CVV " + "x" * 1000 + "\nFor this frozen experiment, today is 17-08-2026."
        issues = lint_deployable_candidate(prompt)
        self.assertIn("frozen calendar date embedded in deployable prompt", issues)
        self.assertIn("dynamic temporal grounding variables missing", issues)


if __name__ == "__main__":
    unittest.main()
