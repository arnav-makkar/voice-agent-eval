"""An unreachable tool endpoint must never be scored as agent misbehaviour.

Campaign 1's v19 round ran while the tool tunnel had been dead for forty
minutes. Every record came back with no tool events, and the post-flight
recorded `required_tool_missing` — a P0 against the agent — on all of them. The
harness could not tell "the agent declined to call the tool" from "the call
never reached the service".

These tests pin the distinction so that cannot recur.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from audit_eva_voice_run import audit_record  # noqa: E402


def _record(tmp: Path, *, transport: dict | None, tool_events: list[str]) -> Path:
    record = tmp / "REC-001"
    record.mkdir(parents=True, exist_ok=True)
    (record / "initial_scenario_db.json").write_text(json.dumps({
        "_current_date": "2026-09-01",
        "evaluation": {"required_actions": [
            {"name": "record_promise_to_pay", "arguments": {"date": "04-09-2026"}},
        ]},
    }), encoding="utf-8")
    (record / "final_scenario_db.json").write_text("{}", encoding="utf-8")
    state: dict = {"events": [{"tool_name": name} for name in tool_events]}
    if transport is not None:
        state["transport"] = transport
    (record / "loopline_tool_state.json").write_text(json.dumps(state), encoding="utf-8")
    (record / "transcript.jsonl").write_text("", encoding="utf-8")
    return record


class TransportVerdictTest(unittest.TestCase):
    def test_unreachable_endpoint_is_invalid_not_an_agent_failure(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            record = _record(
                Path(raw),
                transport={"reachable": False, "reason": "preflight_failed"},
                tool_events=[],
            )
            result = audit_record(record)
        rules = {finding["rule"] for finding in result["findings"]}
        self.assertIn("tool_transport_invalid", rules)
        self.assertNotIn("required_tool_missing", rules)
        self.assertFalse(result["scorable"])

    def test_reachable_endpoint_with_no_call_is_an_agent_failure(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            record = _record(
                Path(raw),
                transport={"reachable": True},
                tool_events=[],
            )
            result = audit_record(record)
        rules = {finding["rule"] for finding in result["findings"]}
        self.assertIn("required_tool_missing", rules)
        self.assertNotIn("tool_transport_invalid", rules)
        self.assertTrue(result["scorable"])

    def test_missing_transport_field_preserves_historical_readings(self) -> None:
        # Every pre-campaign-2 record lacks the field. Those audits must keep
        # their original verdicts rather than being retroactively excused.
        with tempfile.TemporaryDirectory() as raw:
            record = _record(Path(raw), transport=None, tool_events=[])
            result = audit_record(record)
        rules = {finding["rule"] for finding in result["findings"]}
        self.assertIn("required_tool_missing", rules)
        self.assertTrue(result["scorable"])

    def test_a_called_tool_raises_no_finding_either_way(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            record = _record(
                Path(raw),
                transport={"reachable": True},
                tool_events=["record_promise_to_pay"],
            )
            result = audit_record(record)
        rules = {finding["rule"] for finding in result["findings"]}
        self.assertNotIn("required_tool_missing", rules)
        self.assertNotIn("tool_transport_invalid", rules)


if __name__ == "__main__":
    unittest.main()
