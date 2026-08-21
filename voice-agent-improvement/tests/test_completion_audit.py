import json
import tempfile
import unittest
from pathlib import Path

from framework.completion_audit import ARTIFACTS, build


class CompletionAuditTests(unittest.TestCase):
    def test_audit_reports_verification_faithfully(self) -> None:
        """The audit must mirror the verifier, not assert a particular outcome.

        Asserting ``verifier_passed is True`` here deadlocks the suite: this test
        runs *inside* the verifier, so any failure anywhere makes the artifact
        false, which fails this test, which keeps the artifact false. The real
        invariant is that the audit cannot overstate verification — so compare it
        against the recorded run instead.
        """
        with tempfile.TemporaryDirectory() as tmp:
            record = build(Path(tmp) / "audit.json")
        verification_path = ARTIFACTS / "framework" / "verification" / "latest.json"
        expected = json.loads(verification_path.read_text(encoding="utf-8"))["passed"] if verification_path.exists() else False
        self.assertEqual(record["verifier_passed"], expected)

    def test_audit_never_converts_missing_external_evidence_into_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            record = build(Path(tmp) / "audit.json")
        self.assertEqual(record["phases"]["P1_clone_and_spike"][4]["status"], "external_blocked")
        self.assertEqual(record["phases"]["P5_re_evaluation_and_gate"][2]["status"], "external_pending")
        self.assertIn("no live candidate lift", record["claim_boundary"])


if __name__ == "__main__":
    unittest.main()
