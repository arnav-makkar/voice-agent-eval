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
        """A gate may only close when its evidence artifact actually exists.

        The point is not that these gates stay open forever — they are supposed to
        close as evidence lands. The invariant is that closing requires evidence,
        so each status is checked against the artifact it depends on.
        """
        with tempfile.TemporaryDirectory() as tmp:
            record = build(Path(tmp) / "audit.json")

        tool_effect = record["phases"]["P1_clone_and_spike"][4]
        effect_path = ARTIFACTS / "framework" / "emi" / "live_tool_effect.json"
        if tool_effect["status"] == "complete":
            self.assertTrue(effect_path.exists(), "tool gate closed without an evidence artifact")
            evidence = json.loads(effect_path.read_text(encoding="utf-8"))
            # A locally issued call proves the service works, not that the platform
            # can reach it. Only a request from the platform's own caller counts.
            self.assertTrue(
                any(
                    request.get("status") == 200 and request.get("credential_presented")
                    for request in evidence.get("requests_from_platform", [])
                ),
                "tool gate closed without an authenticated request from the platform",
            )
        else:
            self.assertEqual(tool_effect["status"], "external_blocked")

        # The matched suite can be externally pending or deliberately not run
        # after a preserved pilot HOLD. Neither state may be called complete.
        matched_voice = record["phases"]["P5_re_evaluation_and_gate"][2]
        self.assertIn(matched_voice["status"], {"external_pending", "not_run_by_gate"})
        if matched_voice["status"] == "not_run_by_gate":
            decision_path = ARTIFACTS / "framework" / "emi" / "live_voice_pilot_decision.json"
            self.assertTrue(decision_path.exists(), "suite skipped without a pilot decision artifact")
            self.assertEqual(json.loads(decision_path.read_text(encoding="utf-8"))["decision"], "hold")
        self.assertIn("no live candidate lift", record["claim_boundary"].lower())

    def test_owner_label_gate_requires_a_complete_reviewed_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            record = build(Path(tmp) / "audit.json")
        labels = record["phases"]["P0_truth_repair"][0]
        emi = ARTIFACTS / "framework" / "emi"
        if labels["status"] == "complete":
            reviewed = emi / "reference_annotations.owner_reviewed.v1.jsonl"
            self.assertTrue(reviewed.exists())
            count = len([line for line in reviewed.read_text(encoding="utf-8").splitlines() if line.strip()])
            provisional = emi / "reference_annotations.provisional.jsonl"
            expected = len([line for line in provisional.read_text(encoding="utf-8").splitlines() if line.strip()])
            self.assertEqual(count, expected, "owner review must cover every discovery call")
        # The provisional artifact is immutable evidence and must survive.
        self.assertTrue((emi / "reference_annotations.provisional.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
