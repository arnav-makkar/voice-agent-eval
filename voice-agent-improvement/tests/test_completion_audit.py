import tempfile
import unittest
from pathlib import Path

from framework.completion_audit import build


class CompletionAuditTests(unittest.TestCase):
    def test_audit_never_converts_missing_external_evidence_into_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            record = build(Path(tmp) / "audit.json")
        self.assertTrue(record["verifier_passed"])
        self.assertEqual(record["phases"]["P1_clone_and_spike"][4]["status"], "external_blocked")
        self.assertEqual(record["phases"]["P5_re_evaluation_and_gate"][2]["status"], "external_pending")
        self.assertIn("no live candidate lift", record["claim_boundary"])


if __name__ == "__main__":
    unittest.main()
