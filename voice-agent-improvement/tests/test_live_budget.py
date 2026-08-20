import tempfile
import unittest
from pathlib import Path

from framework.evaluation.live_budget import LiveBudgetError, LiveBudgetLedger


class LiveBudgetLedgerTests(unittest.TestCase):
    def ledger(self, path: Path, **overrides) -> LiveBudgetLedger:
        values = dict(max_sessions=2, credit_budget=9, confirmed_live=True)
        values.update(overrides)
        return LiveBudgetLedger(path, **values)

    def test_requires_explicit_confirmation(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger = self.ledger(Path(temp) / "ledger.json", confirmed_live=False)
            with self.assertRaisesRegex(LiveBudgetError, "confirm-live"):
                ledger.reserve(scenario_id="S1", candidate_id="v12", interaction_type="call")

    def test_duplicate_and_session_cap_are_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "ledger.json"
            ledger = self.ledger(path)
            first = ledger.reserve(scenario_id="S1", candidate_id="v12", interaction_type="call")
            ledger.finalize(first, status="failed", error="timeout")
            with self.assertRaisesRegex(LiveBudgetError, "duplicate"):
                ledger.reserve(scenario_id="S1", candidate_id="v12", interaction_type="call")
            ledger.reserve(scenario_id="S2", candidate_id="v12", interaction_type="call")
            with self.assertRaisesRegex(LiveBudgetError, "session cap"):
                ledger.reserve(scenario_id="S3", candidate_id="v12", interaction_type="call")

    def test_credit_budget_counts_failed_attempts(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "ledger.json"
            ledger = self.ledger(path, max_sessions=4, credit_budget=5)
            reservation = ledger.reserve(scenario_id="S1", candidate_id="v12", interaction_type="call")
            ledger.finalize(reservation, status="failed")
            with self.assertRaisesRegex(LiveBudgetError, "credit budget"):
                ledger.reserve(scenario_id="S2", candidate_id="v12", interaction_type="call")


if __name__ == "__main__":
    unittest.main()
