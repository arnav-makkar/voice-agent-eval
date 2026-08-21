import json
import unittest
from datetime import date
from pathlib import Path

from scripts.audit_eva_voice_run import audit_run


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "framework" / "emi" / "eva_voice_suite_v3_hinglish_fixed" / "manifest.json"
SCENARIOS = ROOT / "research" / "upstream" / "eva" / "data" / "emi_scenarios"
FAILED_V19 = ROOT / "artifacts" / "eva_pilots" / "emi_eva_v19_pilots_20260821_160827"


class HinglishVoiceSuiteV3Test(unittest.TestCase):
    def test_active_suite_is_18_hinglish_records_with_three_fixed_pilots(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(len(manifest["records"]), 18)
        self.assertEqual(
            manifest["pilot_record_ids"],
            ["EMI-HINGLISH-FIXED-001", "EMI-HINGLISH-FIXED-002", "EMI-HINGLISH-FIXED-003"],
        )
        self.assertEqual({row["language"] for row in manifest["records"]}, {"hinglish"})

    def test_no_required_tool_date_precedes_frozen_current_date(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for record in manifest["records"]:
            scenario = json.loads((SCENARIOS / f"{record['record_id']}.json").read_text(encoding="utf-8"))
            current = date.fromisoformat(scenario["_current_date"])
            for action in scenario["evaluation"]["required_actions"]:
                value = action.get("arguments", {}).get("date")
                if value:
                    day, month, year = value.split("-")
                    self.assertGreaterEqual(date(int(year), int(month), int(day)), current, record["record_id"])

    def test_failed_v19_run_remains_rejected_by_postflight(self) -> None:
        report = audit_run(FAILED_V19)
        self.assertEqual(report["decision"], "HOLD")
        self.assertIn("required_tool_missing", report["decision_reasons"])
        self.assertIn("terminal_claim_without_tool_evidence", report["decision_reasons"])
        self.assertIn("non_hinglish_indic_script", report["decision_reasons"])


if __name__ == "__main__":
    unittest.main()
