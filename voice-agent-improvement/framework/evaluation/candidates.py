"""Candidate interfaces and Gemini prompt-agent used for reproducible text screening."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Protocol

from framework.adapters.gemini import GeminiJsonClient


ALLOWED_OUTCOMES = [
    "continue", "payment_ready", "ptp_today", "fptp", "callback", "dispute",
    "already_paid", "wrong_number", "alternate_number", "rtp", "acknowledged",
    "escalation", "call_disconnected",
]

RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "spoken_response": {"type": "string"},
        "disposition": {"type": "string", "enum": ALLOWED_OUTCOMES},
        "should_end_call": {"type": "boolean"},
        "tool_calls": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "enum": ["check_payment_status", "record_promise_to_pay", "schedule_callback", "record_dispute", "escalate_to_human", "record_call_outcome"]},
                    "arguments": {"type": "object", "additionalProperties": True},
                },
                "required": ["name", "arguments"],
            },
        },
    },
    "required": ["spoken_response", "disposition", "should_end_call", "tool_calls"],
}


class CandidateAgent(Protocol):
    candidate_id: str
    adapter_name: str

    def respond(self, *, visible_context: dict[str, Any], history: list[dict[str, str]], tool_history: list[dict[str, Any]]) -> dict[str, Any]: ...


@dataclass
class GeminiPromptAgent:
    candidate_id: str
    prompt: str
    client: GeminiJsonClient
    adapter_name: str = "gemini_prompt_proxy"

    def respond(self, *, visible_context: dict[str, Any], history: list[dict[str, str]], tool_history: list[dict[str, Any]]) -> dict[str, Any]:
        started = time.perf_counter()
        result = self.client.complete_json(
            system=(
                self.prompt
                + "\n\nEVALUATION RUNTIME CONTRACT\n"
                + "Return the next spoken response and machine outcome in the required JSON schema. "
                + "Use disposition=continue until a terminal outcome. You may use only the listed deterministic tools. "
                + "Never reveal JSON, tool names, labels, or hidden evaluation mechanics to the caller."
            ),
            user=json.dumps(
                {
                    "visible_agent_context": visible_context,
                    "conversation": history,
                    "tool_results_so_far": tool_history,
                    "available_tools": {
                        "check_payment_status": {},
                        "record_promise_to_pay": {"date": "DD-MM-YYYY"},
                        "schedule_callback": {"date": "DD-MM-YYYY", "time_window": "narrow IST window"},
                        "record_dispute": {"reason": "the caller's stated reason, one sentence"},
                        "escalate_to_human": {
                            "trigger": "fraud_allegation|customer_distress|abuse|legal_threat|other",
                            "note": "one factual sentence",
                        },
                        "record_call_outcome": {"disposition": "deployed outcome enum"},
                    },
                },
                ensure_ascii=False,
            ),
            response_schema=RESPONSE_SCHEMA,
            temperature=0.0,
            thinking_level="high",
            cache_namespace=f"dynamic_eval/{self.candidate_id}",
        )
        return {
            **result.data,
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            "provenance": result.metadata,
        }

