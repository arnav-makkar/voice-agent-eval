"""The two tools added in campaign 2 must behave identically in both tiers.

`record_dispute` and `escalate_to_human` exist twice: once as an HTTP route the
deployed Indus agent calls, and once as an in-process branch the text tier
executes. If those two drift, a scenario can pass in text and fail on the
platform (or the reverse) for reasons that have nothing to do with the agent.

These tests pin the contract that keeps them the same: the accepted trigger
values, the required fields, and the disposition each tool writes.
"""

from __future__ import annotations

import unittest

from framework.evaluation.environment import (
    ESCALATION_TRIGGERS,
    EMIEnvironment,
    ToolExecutionError,
)
from framework.tool_service import EscalationRequest


def _env() -> EMIEnvironment:
    return EMIEnvironment.from_initial(
        {"current_date": "21-08-2026", "outstanding_amount": 4416, "payment_status": "unpaid"}
    )


class NewToolContractTest(unittest.TestCase):
    def test_text_tier_triggers_match_the_deployed_route(self) -> None:
        # The HTTP model is the source of truth; the text tier mirrors it.
        deployed = set(EscalationRequest.model_fields["trigger"].annotation.__args__)
        self.assertEqual(ESCALATION_TRIGGERS, deployed)

    def test_record_dispute_writes_the_reason_and_the_disposition(self) -> None:
        env = _env()
        result = env.execute("record_dispute", {"reason": "The TV was returned"})
        self.assertTrue(result["recorded"])
        self.assertEqual(env.state["dispute_reason"], "The TV was returned")
        self.assertEqual(env.state["disposition"], "dispute")

    def test_record_dispute_requires_a_reason(self) -> None:
        # A dispute with no stated reason is not a record anyone can act on.
        with self.assertRaises(ToolExecutionError):
            _env().execute("record_dispute", {"reason": "   "})

    def test_escalation_writes_trigger_note_and_disposition(self) -> None:
        env = _env()
        result = env.execute(
            "escalate_to_human",
            {"trigger": "customer_distress", "note": "Caller lost their job."},
        )
        self.assertEqual(result["disposition"], "escalation")
        self.assertEqual(env.state["escalation"]["trigger"], "customer_distress")
        self.assertEqual(env.state["disposition"], "escalation")

    def test_escalation_rejects_a_trigger_outside_the_enum(self) -> None:
        # An unconstrained trigger would make escalation reasons unaggregatable.
        with self.assertRaises(ToolExecutionError):
            _env().execute("escalate_to_human", {"trigger": "annoyed", "note": "x"})

    def test_escalation_requires_a_note(self) -> None:
        with self.assertRaises(ToolExecutionError):
            _env().execute("escalate_to_human", {"trigger": "abuse", "note": ""})

    def test_both_tools_count_as_writes_for_the_say_vs_do_rule(self) -> None:
        # The observed campaign-2 baseline defect: the agent said "I am recording
        # this" and called nothing. That is only detectable if these are writes.
        from framework.evaluation.verifier import WRITE_TOOLS

        self.assertIn("record_dispute", WRITE_TOOLS)
        self.assertIn("escalate_to_human", WRITE_TOOLS)


if __name__ == "__main__":
    unittest.main()
