import unittest
import json
import tempfile
from pathlib import Path

from framework.release.gate import _paired_bootstrap, compare


class ReleaseGateTests(unittest.TestCase):
    @staticmethod
    def row(case_id: str, *, split: str = "development", reviewed: bool = True) -> dict:
        return {
            "case": {
                "case_id": case_id,
                "split": split,
                "failure_family": "test_family",
                "reviewer_status": "reviewed" if reviewed else "provisional",
            },
            "deterministic": {"hard_gate_pass": True},
            "semantic": {
                "task_success": True,
                "terminal_state_correct": True,
                "hard_safety_violation": False,
                "integrity_violation": False,
                "factual_error": False,
                "forbidden_behavior_violation": False,
                "directness_score": 4,
                "conversation_quality_score": 4,
                "evidence": "test evidence",
            },
        }

    @staticmethod
    def compare_rows(baseline: list[dict], candidate: list[dict]) -> dict:
        with tempfile.TemporaryDirectory() as directory:
            baseline_path = Path(directory) / "baseline.jsonl"
            candidate_path = Path(directory) / "candidate.jsonl"
            baseline_path.write_text("\n".join(json.dumps(row) for row in baseline) + "\n", encoding="utf-8")
            candidate_path.write_text("\n".join(json.dumps(row) for row in candidate) + "\n", encoding="utf-8")
            return compare(baseline_path, candidate_path)

    def test_paired_bootstrap_detects_uniform_improvement(self) -> None:
        evidence = _paired_bootstrap([1.0] * 20)
        self.assertEqual(evidence["mean"], 1.0)
        self.assertGreater(evidence["ci_low"], 0)

    def test_paired_bootstrap_does_not_invent_lift(self) -> None:
        evidence = _paired_bootstrap([0.0] * 20)
        self.assertEqual(evidence["mean"], 0.0)
        self.assertEqual(evidence["probability_positive"], 0.0)

    def test_forbidden_behavior_regression_is_rejected(self) -> None:
        base = self.row("C1")
        candidate = json.loads(json.dumps(base))
        candidate["semantic"]["forbidden_behavior_violation"] = True
        decision = self.compare_rows([base], [candidate])
        self.assertEqual(decision["decision"], "reject_new_severe_regression")
        self.assertEqual(decision["new_severe_regressions"][0]["case_id"], "C1")

    def test_aggregate_improvement_cannot_hide_new_integrity_regression(self) -> None:
        base_one = self.row("C1")
        base_one["semantic"]["task_success"] = False
        base_one["semantic"]["integrity_violation"] = True
        base_two = self.row("C2")
        candidate_one = json.loads(json.dumps(base_one))
        candidate_one["semantic"]["task_success"] = True
        candidate_one["semantic"]["integrity_violation"] = False
        candidate_two = json.loads(json.dumps(base_two))
        candidate_two["semantic"]["integrity_violation"] = True
        decision = self.compare_rows([base_one, base_two], [candidate_one, candidate_two])
        self.assertLessEqual(decision["candidate_metrics"]["integrity"], decision["baseline_metrics"]["integrity"])
        self.assertEqual(decision["decision"], "reject_new_severe_regression")
        self.assertIn("C2", [row["case_id"] for row in decision["new_severe_regressions"]])

    def test_terminal_state_regression_is_rejected(self) -> None:
        base = self.row("C1")
        candidate = json.loads(json.dumps(base))
        candidate["semantic"]["terminal_state_correct"] = False
        decision = self.compare_rows([base], [candidate])
        self.assertEqual(decision["decision"], "reject_new_severe_regression")
        self.assertEqual(decision["new_severe_regressions"][0]["type"], "terminal_state_regression")

    def test_passing_candidate_still_requires_owner_truth(self) -> None:
        base = self.row("C1", reviewed=False)
        base["semantic"]["task_success"] = False
        candidate = json.loads(json.dumps(base))
        candidate["semantic"]["task_success"] = True
        decision = self.compare_rows([base], [candidate])
        self.assertEqual(decision["decision"], "hold_owner_truth_required")
        self.assertTrue(decision["release_routes"]["route_a_more_task_wins"])

    def test_route_b_allows_equal_task_count_with_fewer_quality_failures(self) -> None:
        base = self.row("C1")
        base["semantic"]["integrity_violation"] = True
        candidate = json.loads(json.dumps(base))
        candidate["semantic"]["integrity_violation"] = False
        decision = self.compare_rows([base], [candidate])
        self.assertTrue(decision["release_routes"]["route_b_task_non_degradation_plus_quality"])
        self.assertEqual(decision["decision"], "eligible_for_fresh_group_separated_final_test")


if __name__ == "__main__":
    unittest.main()
