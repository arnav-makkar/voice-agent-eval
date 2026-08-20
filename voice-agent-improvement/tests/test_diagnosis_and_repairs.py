import unittest

from framework.diagnosis.router import route_failure
from framework.repairs.registry import repair_engine


class DiagnosisAndRepairTests(unittest.TestCase):
    def test_prompt_failure_routes_to_manual_and_gepa(self) -> None:
        route = route_failure("agent_prompt", True)
        self.assertEqual(route["candidate_engines"], ["manual_prompt", "gepa"])
        self.assertEqual(repair_engine("gepa")["surface"], "prompt")

    def test_non_prompt_failure_cannot_be_sent_to_gepa(self) -> None:
        route = route_failure("output_extractor", False)
        self.assertEqual(route["candidate_engines"], ["extractor_config", "judge_alignment"])
        self.assertNotIn("gepa", route["candidate_engines"])

    def test_mixed_failure_requires_ablation(self) -> None:
        route = route_failure("mixed", None)
        self.assertEqual(route["primary_engine"], "triage_ablation")
        self.assertIn("one component", route["isolation"])


if __name__ == "__main__":
    unittest.main()
