import json
import tempfile
import unittest
from pathlib import Path

from framework.core.schemas import EvaluationCase
from framework.domain import list_domain_packs, load_domain_pack
from framework.ingestion.canonicalize import canonicalize


class FrameworkCoreTests(unittest.TestCase):
    def test_domain_packs_are_valid_and_domain_specific(self) -> None:
        self.assertEqual(list_domain_packs(), ["emi_recovery", "hospital_appointments"])
        emi = load_domain_pack("emi_recovery")
        hospital = load_domain_pack("hospital_appointments")
        self.assertEqual(emi.metric_contract["primary"], "eligible_call_tsr")
        self.assertEqual(hospital.metric_contract["primary"], "task_resolution_rate")
        self.assertNotEqual(emi.task_contract["accepted_terminal_states"], hospital.task_contract["accepted_terminal_states"])

    def test_evaluation_case_rejects_hidden_key_leakage(self) -> None:
        with self.assertRaisesRegex(ValueError, "hidden caller state leaked"):
            EvaluationCase(
                schema_version="evaluation-case.v1",
                case_id="C-1",
                domain_id="emi_recovery",
                domain_pack_version="1.0.0",
                failure_family="trust_resolution",
                test_type="counterfactual",
                split="development",
                language="en-IN",
                visible_agent_context={"caller_intent": "unknown"},
                hidden_caller_state={"caller_intent": "will_pay_if_safe"},
                environment_state={},
                expected_transition="payment_ready",
                accepted_terminal_states=["payment_ready"],
                forbidden_behaviors=["invent facts"],
                exact_facts={},
                lineage={"seed_trace_id": "BL-V12-03-R1"},
            )

    def test_canonicalize_all_twenty_real_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = canonicalize(output_dir=Path(temporary))
            self.assertEqual(result["metadata"]["reference_status"], "provisional")
            traces = [json.loads(line) for line in (Path(temporary) / "traces.jsonl").read_text().splitlines()]
            refs = [json.loads(line) for line in (Path(temporary) / "reference_annotations.provisional.jsonl").read_text().splitlines()]
            self.assertEqual(len(traces), 20)
            self.assertEqual(len(refs), 20)
            self.assertTrue(all(row["source"]["recording_type"] == "real_voice" for row in traces))
            self.assertTrue(all(row["review_status"] == "provisional" for row in refs))
            self.assertEqual(len({row["content_hash"] for row in traces}), 20)


if __name__ == "__main__":
    unittest.main()
