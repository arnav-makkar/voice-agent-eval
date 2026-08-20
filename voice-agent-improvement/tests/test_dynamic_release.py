import json
import tempfile
import unittest
from pathlib import Path

from framework.evaluation.release import decide
from framework.evaluation.select_candidate import choose
from framework.evaluation.final_decision import decide as decide_final


def metric(sid, success, *, forbidden=True, environment=True, actions=True, experience=1.0):
    return {
        "scenario_id": sid,
        "task_success": success,
        "valid_simulation": True,
        "accuracy": {
            "forbidden_behavior": forbidden,
            "environment_state": environment,
            "required_actions": actions,
        },
        "experience": {"score": experience},
        "failure_localization": None if success else {"component": "agent_policy"},
    }


class DynamicReleaseTests(unittest.TestCase):
    def write(self, path, rows):
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def test_more_wins_with_no_regression_advances(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); before=root/"b.jsonl"; after=root/"a.jsonl"; output=root/"d.json"
            self.write(before, [metric("1", False), metric("2", True)])
            self.write(after, [metric("1", True), metric("2", True)])
            result = decide(before, after, output)
            self.assertEqual(result["decision"], "eligible_for_fresh_final_test")

    def test_new_forbidden_failure_rejects_average_gain(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); before=root/"b.jsonl"; after=root/"a.jsonl"; output=root/"d.json"
            self.write(before, [metric("1", False), metric("2", True)])
            self.write(after, [metric("1", True), metric("2", False, forbidden=False)])
            result = decide(before, after, output)
            self.assertEqual(result["decision"], "reject_new_severe_regression")
            self.assertTrue(any(item["severity"] == "P0" for item in result["regressions"]))

    def test_experience_collapse_blocks_route_a(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); before=root/"b.jsonl"; after=root/"a.jsonl"; output=root/"d.json"
            self.write(before, [metric("1", False, experience=1.0), metric("2", True, experience=1.0)])
            self.write(after, [metric("1", True, experience=0.7), metric("2", True, experience=0.7)])
            result = decide(before, after, output)
            self.assertEqual(result["decision"], "hold_no_predeclared_improvement_route")
            self.assertFalse(result["conditions"]["experience_drop_within_10pp"])

    def test_exact_paired_diagnostic_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); before=root/"b.jsonl"; after=root/"a.jsonl"; output=root/"d.json"
            self.write(before, [metric(str(index), False) for index in range(4)])
            self.write(after, [metric(str(index), True) for index in range(4)])
            result = decide(before, after, output)
            self.assertEqual(result["paired_task_evidence"]["discordant_pairs"], 4)
            self.assertEqual(result["paired_task_evidence"]["exact_two_sided_p"], 0.125)

    def test_candidate_selection_rejects_higher_semantic_but_ineligible_arm(self):
        arms = [
            {"candidate_id": "safe", "prompt_path": "safe.md", "prompt_sha256": "a", "prompt_bytes": 10, "release_path": "safe.json", "release": {"decision": "eligible_for_fresh_final_test", "candidate_task_successes": 9, "candidate_experience": 0.9}, "semantic": {"average_progression": 3.8}},
            {"candidate_id": "regressed", "prompt_path": "bad.md", "prompt_sha256": "b", "prompt_bytes": 9, "release_path": "bad.json", "release": {"decision": "reject_new_severe_regression", "candidate_task_successes": 10, "candidate_experience": 1.0}, "semantic": {"average_progression": 4.0}},
        ]
        self.assertEqual(choose(arms)["selected_candidate_id"], "safe")

    def test_fresh_final_interpreter_requires_exact_frozen_access(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paired = root / "paired.json"
            seal = root / "seal.json"
            access = root / "access.json"
            output = root / "decision.json"
            paired.write_text(json.dumps({
                "decision": "eligible_for_fresh_final_test",
                "matched_scenarios": 12,
                "baseline_task_successes": 5,
                "candidate_task_successes": 9,
                "repairs": ["4"],
                "task_regressions": [],
                "regressions": [],
                "baseline_experience": 1.0,
                "candidate_experience": 0.94,
                "conditions": {
                    "zero_new_severe_regressions": True,
                    "all_baseline_task_wins_preserved": True,
                    "experience_drop_within_10pp": True,
                },
                "paired_task_evidence": {"exact_two_sided_p": 0.125},
            }), encoding="utf-8")
            seal.write_text(json.dumps({
                "records": 12,
                "dataset_sha256": "dataset",
                "baseline_frozen_sha256": "base",
                "candidate_method_frozen_sha256": "candidate",
            }), encoding="utf-8")
            access.write_text(json.dumps({
                "accessed_by_improvement": False,
                "evaluation_runs": [
                    {"candidate_hash": "base"},
                    {"candidate_hash": "candidate"},
                ],
            }), encoding="utf-8")
            result = decide_final(paired, seal, access, output)
            self.assertTrue(result["protocol_valid"])
            self.assertEqual(result["decision"], "pass_text_final_awaiting_matched_voice")


if __name__ == "__main__":
    unittest.main()
