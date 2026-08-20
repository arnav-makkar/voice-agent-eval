import unittest

from dataset.generate_scenarios import build_scenario
from dataset.simulation import (
    ModelResult,
    agent_prompt,
    caller_prompt,
    render_initial_message,
    run_fixture_rollout,
    run_model_rollout,
)


PROMPT = "You are Shubh, a direct EMI recovery agent."
OPENING = "Hi, am I speaking to @userName?"


class QueueModel:
    def __init__(self, model_name, values):
        self.model_name = model_name
        self.values = iter(values)

    def complete_json(self, system, user, *, seed):
        return ModelResult(value=next(self.values), latency_ms=1, usage={"total_tokens": 10})


class SimulationTests(unittest.TestCase):
    def test_fixture_is_clearly_non_evidentiary_and_auditable(self):
        scenario = build_scenario(0)
        record = run_fixture_rollout(
            scenario,
            candidate_id="indus-v10",
            candidate_prompt=PROMPT,
            initial_message=OPENING,
        )
        self.assertFalse(record["generation"]["benchmark_evidence"])
        self.assertEqual(record["scenario_contract_sha256"], scenario["contract_sha256"])
        self.assertIn(scenario["public_environment"]["runtime_inputs"]["userName"], record["turns"][0]["text"])

    def test_agent_prompt_does_not_receive_private_state(self):
        scenario = build_scenario(0)
        _, caller_user = caller_prompt(scenario, [{"speaker": "agent", "text": "Hello"}])
        _, agent_user = agent_prompt(PROMPT, scenario, [{"speaker": "user", "text": "Haan"}])
        self.assertIn("conversion_rule", caller_user)
        self.assertNotIn("conversion_rule", agent_user)
        self.assertNotIn(scenario["private_user_state"]["objection"], agent_user)

    def test_model_rollout_alternates_isolated_models_and_stops(self):
        scenario = build_scenario(0)
        caller = QueueModel("caller-test", [{
            "utterance": "Haan, app kholkar abhi pay karta hoon.",
            "hang_up": False,
            "terminal_state": "payment_ready",
            "state_note": "accepted",
        }])
        agent = QueueModel("agent-test", [{"utterance": "Theek hai, official app use kijiye.", "end_call": True}])
        record = run_model_rollout(
            scenario,
            candidate_id="indus-v10",
            candidate_prompt=PROMPT,
            initial_message=OPENING,
            caller_model=caller,
            agent_model=agent,
        )
        self.assertEqual([turn["speaker"] for turn in record["turns"]], ["agent", "user", "agent"])
        self.assertEqual(record["simulator_labels"]["terminal_state"], "payment_ready")
        self.assertIsNone(record["simulator_labels"]["primary_success_observed"])

    def test_initial_message_rendering(self):
        self.assertEqual(render_initial_message(OPENING, {"userName": "Arnav"}), "Hi, am I speaking to Arnav?")


if __name__ == "__main__":
    unittest.main()
