from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from framework.evaluation.live_release import compare_live_suites


def write_record(root: Path, record: str, *, task: float, x: float, faith: float = 1.0) -> None:
    target = root / "records" / record
    target.mkdir(parents=True)
    metrics = {
        "metrics": {
            "task_completion": {"normalized_score": task},
            "faithfulness": {"normalized_score": faith},
            "agent_speech_fidelity": {"normalized_score": 1.0},
            "turn_taking": {"normalized_score": x},
            "conciseness": {"normalized_score": 1.0},
            "conversation_progression": {"normalized_score": x},
        },
        "aggregate_metrics": {},
    }
    (target / "metrics.json").write_text(json.dumps(metrics))
    (target / "result.json").write_text(json.dumps({"completed": True}))


class LiveReleaseTest(unittest.TestCase):
    def test_business_route_requires_no_task_regression(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            baseline, candidate = root / "b", root / "c"
            write_record(baseline, "A", task=0, x=0.5)
            write_record(baseline, "B", task=1, x=1)
            write_record(candidate, "A", task=1, x=1)
            write_record(candidate, "B", task=1, x=1)
            result = compare_live_suites(baseline, candidate)
            self.assertEqual(result["decision"], "promote_business_win_route")

    def test_quality_route_is_separate_from_task_lift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            baseline, candidate = root / "b", root / "c"
            write_record(baseline, "A", task=1, x=0.5)
            write_record(candidate, "A", task=1, x=1)
            result = compare_live_suites(baseline, candidate)
            self.assertEqual(result["decision"], "promote_quality_route_no_tsr_claim")
            self.assertFalse(result["routes"]["business_win"])

    def test_new_faithfulness_failure_holds(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            baseline, candidate = root / "b", root / "c"
            write_record(baseline, "A", task=1, x=0.5)
            write_record(candidate, "A", task=1, x=1, faith=0)
            result = compare_live_suites(baseline, candidate)
            self.assertEqual(result["decision"], "hold")
            self.assertEqual(len(result["new_p0"]), 1)

    def test_mismatched_suite_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            baseline, candidate = root / "b", root / "c"
            write_record(baseline, "A", task=1, x=1)
            write_record(candidate, "B", task=1, x=1)
            with self.assertRaises(ValueError):
                compare_live_suites(baseline, candidate)


if __name__ == "__main__":
    unittest.main()
