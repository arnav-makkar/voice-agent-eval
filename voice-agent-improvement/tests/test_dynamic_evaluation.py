import tempfile
import unittest
from pathlib import Path

from framework.evaluation.build_emi_scenarios import build
from framework.evaluation.contracts import EvaluationScenario, UserStep
from framework.evaluation.metrics import evaluate_run
from framework.evaluation.runner import load_scenarios, run_scenario
from framework.evaluation.adapters.indus import apply_pcm_perturbations
from framework.evaluation.build_fresh_final import _validate_blueprints
from array import array


class ScriptAgent:
    adapter_name = "test_script"

    def __init__(self, responses, candidate_id="script"):
        self.responses = list(responses)
        self.candidate_id = candidate_id

    def respond(self, **_kwargs):
        return {**self.responses.pop(0), "latency_ms": 10, "provenance": {"test": True}}


def scenario(**overrides):
    values = dict(
        schema_version="evaluation-scenario.v1",
        scenario_id="T-1",
        domain_id="emi_recovery",
        split="development",
        source_group="g-1",
        failure_family="future_promise",
        language="hinglish",
        user_goal="promise a date",
        persona={"patience": "low"},
        visible_context={"currentDate": "17-08-2026"},
        hidden_state={"target": "fptp"},
        initial_environment={"current_date": "17-08-2026", "payment_status": "unpaid", "disposition": None},
        user_steps=[UserStep("haan", "ack"), UserStep("20 August ko pay karunga", "promise")],
        accepted_dispositions=["fptp"],
        expected_state={"disposition": "fptp", "promise_to_pay_date": "20-08-2026"},
        required_actions=[{"name": "record_promise_to_pay", "arguments": {"date": "20-08-2026"}}],
    )
    values.update(overrides)
    return EvaluationScenario(**values)


class DynamicEvaluationTests(unittest.TestCase):
    def test_stateful_tool_success(self):
        agent = ScriptAgent([
            {"spoken_response": "Ji, payment kab karenge?", "disposition": "continue", "should_end_call": False, "tool_calls": []},
            {"spoken_response": "20 August confirm. Dhanyavaad.", "disposition": "fptp", "should_end_call": True, "tool_calls": [{"name": "record_promise_to_pay", "arguments": {"date": "20-08-2026"}}]},
        ])
        card = scenario()
        run = run_scenario(agent, card, "hash")
        metrics = evaluate_run(card, run)
        self.assertTrue(metrics["task_success"])
        self.assertEqual(run.final_state["promise_to_pay_date"], "20-08-2026")
        self.assertEqual(metrics["first_failure"], None)

    def test_missing_tool_is_localized(self):
        agent = ScriptAgent([
            {"spoken_response": "Payment kab karenge?", "disposition": "continue", "should_end_call": False, "tool_calls": []},
            {"spoken_response": "20 August noted.", "disposition": "fptp", "should_end_call": True, "tool_calls": []},
        ])
        card = scenario()
        metrics = evaluate_run(card, run_scenario(agent, card, "hash"))
        self.assertFalse(metrics["task_success"])
        self.assertEqual(metrics["first_failure"], "environment_state")
        self.assertEqual(metrics["failure_localization"]["component"], "tool_or_state_transition")

    def test_eva_taxonomy_is_versioned_and_missing_audio_metrics_are_explicit(self):
        agent = ScriptAgent([
            {"spoken_response": "20 August confirm. Dhanyavaad.", "disposition": "fptp", "should_end_call": True, "tool_calls": [{"name": "record_promise_to_pay", "arguments": {"date": "20-08-2026"}}]},
        ])
        metrics = evaluate_run(scenario(user_steps=[UserStep("20 August ko pay karunga", "promise")]), run_scenario(agent, scenario(user_steps=[UserStep("20 August ko pay karunga", "promise")]), "hash"))
        self.assertEqual(metrics["schema_version"], "evaluation-metrics.v3")
        self.assertEqual(metrics["evaluator_adapter"]["version"], "framework-eva-adapter.v1")
        self.assertEqual(metrics["eva"]["accuracy"]["task_completion"]["score"], 1.0)
        self.assertEqual(metrics["eva"]["accuracy"]["agent_speech_fidelity"]["score"], None)
        self.assertEqual(metrics["eva"]["validation"]["user_speech_fidelity"]["status"], "unavailable")
        self.assertEqual(metrics["eva"]["experience"]["turn_taking"]["status"], "not_exercised")

    def test_cross_script_asr_is_unscored_instead_of_fake_zero(self):
        card = scenario(user_steps=[UserStep("haan boliye", "ack")], required_actions=[])
        agent = ScriptAgent([{
            "spoken_response": "Ji boliye.",
            "disposition": "fptp",
            "should_end_call": True,
            "tool_calls": [{"name": "record_promise_to_pay", "arguments": {"date": "20-08-2026"}}],
        }])
        run = run_scenario(agent, card, "hash")
        run.provenance["caller_actions"] = [{"action": "speak", "text": "haan boliye"}]
        run.provenance["observed_user_transcripts"] = ["हां बोलिए"]
        metrics = evaluate_run(card, run)
        speech = metrics["eva"]["validation"]["user_speech_fidelity"]
        self.assertEqual(speech["status"], "script_mismatch_unscored")
        self.assertIsNone(speech["stt_wer"])

    def test_dataset_is_group_separated(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            result = build(output)
            self.assertEqual(result["validation"]["total"], 30)
            self.assertTrue(result["validation"]["group_independence_pass"])
            self.assertEqual(len(load_scenarios(output / "development.jsonl")), 18)
            self.assertEqual(len(load_scenarios(output / "validation.jsonl")), 6)
            self.assertEqual(len(load_scenarios(output / "regression.jsonl")), 6)

    def test_credential_safety_advice_is_not_a_forbidden_hit(self):
        card = scenario(
            accepted_dispositions=["acknowledged"],
            expected_state={"disposition": "acknowledged"},
            required_actions=[],
            forbidden_phrases=["otp"],
            user_steps=[UserStep("OTP bata doon?", "credential_offer")],
        )
        agent = ScriptAgent([
            {
                "spoken_response": "OTP kisi ko mat dijiye. Official app mein privately enter kijiye.",
                "disposition": "acknowledged",
                "should_end_call": True,
                "tool_calls": [{"name": "record_call_outcome", "arguments": {"disposition": "acknowledged"}}],
            }
        ])
        metrics = evaluate_run(card, run_scenario(agent, card, "hash"))
        self.assertEqual(metrics["forbidden_hits"], [])
        self.assertTrue(metrics["accuracy"]["forbidden_behavior"])

    def test_hinglish_mat_share_is_safety_not_solicitation(self):
        card = scenario(
            accepted_dispositions=["acknowledged"],
            expected_state={"disposition": "acknowledged"},
            required_actions=[],
            forbidden_phrases=["otp"],
            user_steps=[UserStep("OTP bata doon?", "credential_offer")],
        )
        agent = ScriptAgent([{
            "spoken_response": "Nahi, OTP kisi ko mat share karein. App mein khud enter karein.",
            "disposition": "acknowledged",
            "should_end_call": True,
            "tool_calls": [{"name": "record_call_outcome", "arguments": {"disposition": "acknowledged"}}],
        }])
        metrics = evaluate_run(card, run_scenario(agent, card, "hash"))
        self.assertEqual(metrics["forbidden_hits"], [])

    def test_audio_perturbations_are_deterministic_and_length_safe(self):
        pcm = array("h", [1000, -1000] * 1600).tobytes()
        labels = ["background_noise_12db", "packet_loss_5pct", "low_volume_12db"]
        first = apply_pcm_perturbations(pcm, labels, seed=7)
        second = apply_pcm_perturbations(pcm, labels, seed=7)
        self.assertEqual(first, second)
        self.assertEqual(len(first), len(pcm))
        faster = apply_pcm_perturbations(pcm, ["fast_speech_1_25x"], seed=7)
        self.assertLess(len(faster), len(pcm))

    def test_fresh_final_contract_validator_blocks_internal_leakage(self):
        base = {
            "failure_family": "conditional",
            "language": "hinglish",
            "user_goal": "respond",
            "persona": {"patience": "low"},
            "user_steps": [{"text": "I know this evaluation scenario id", "intent": "leak"}],
            "accepted_disposition": "acknowledged",
            "required_tool": "none",
            "tool_arguments": {},
            "perturbations": [],
        }
        with self.assertRaises(ValueError):
            _validate_blueprints([dict(base) for _ in range(12)])


if __name__ == "__main__":
    unittest.main()
