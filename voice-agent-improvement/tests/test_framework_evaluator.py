import unittest

from framework.evaluators.deterministic import evaluate_response


class DeterministicEvaluatorTests(unittest.TestCase):
    def case(self):
        return {
            "case_id": "C-1",
            "visible_agent_context": {
                "conversation_history": [{"actor": "caller", "content": "Yes, I will pay now."}],
                "latest_caller_utterance": "I said I will do it now.",
            },
            "environment_state": {"verified_platform_actions": []},
            "forbidden_behaviors": ["ask the caller to confirm payment again"],
        }

    def test_redundant_confirmation_and_completion_claim_fail(self):
        result = evaluate_response(
            self.case(),
            {"spoken_response": "Your payment is completed. Will you pay now?"},
        )
        self.assertTrue(result["redundant_confirmation"])
        self.assertTrue(result["unsupported_completion_claim"])
        self.assertFalse(result["hard_gate_pass"])

    def test_concise_close_passes(self):
        result = evaluate_response(
            self.case(),
            {"spoken_response": "Thank you. Please use the official app. Have a good day."},
        )
        self.assertFalse(result["redundant_confirmation"])
        self.assertFalse(result["unsupported_completion_claim"])
        self.assertTrue(result["hard_gate_pass"])


if __name__ == "__main__":
    unittest.main()
