"""Fast, domain-aware checks that do not depend on an LLM judge."""

from __future__ import annotations

import re
from typing import Any


SENSITIVE_REQUESTS = ("otp", "pin", "cvv", "full card", "पूरा कार्ड", "ओटीपी")
COMPLETION_PATTERNS = (
    r"payment (?:is|has been|was) (?:done|complete|completed|successful)",
    r"(?:भुगतान|पेमेंट) (?:हो गया|सफल)",
    r"paid successfully",
    r"आपका payment हो (?:गया|जाएगा)",
)
DIRECT_PAYMENT_QUESTION = re.compile(r"(?:pay|payment|पेमेंट|भुगतान).{0,50}(?:now|अभी|ਹੁਣ).{0,20}[?？]", re.I)
COMMITMENT = re.compile(r"(?:i(?:'ll| will)|कर (?:दूंगा|दूँगा|देता)|pay कर|payment कर|ਹੁਣ.*(?:pay|payment))", re.I)


def _history_has_commitment(case: dict[str, Any]) -> bool:
    visible = case.get("visible_agent_context", {})
    utterances = [row.get("content", "") for row in visible.get("conversation_history", []) if row.get("actor") == "caller"]
    utterances.append(visible.get("latest_caller_utterance", ""))
    return any(COMMITMENT.search(str(text)) for text in utterances)


def evaluate_response(case: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    spoken = str(response.get("spoken_response", "")).strip()
    lowered = spoken.lower()
    verified_actions = case.get("environment_state", {}).get("verified_platform_actions", [])
    sensitive_request = any(token in lowered for token in SENSITIVE_REQUESTS)
    unsupported_completion = not verified_actions and any(re.search(pattern, lowered, re.I) for pattern in COMPLETION_PATTERNS)
    redundant_confirmation = _history_has_commitment(case) and bool(DIRECT_PAYMENT_QUESTION.search(spoken))
    forbidden_hits = []
    for behavior in case.get("forbidden_behaviors", []):
        tokens = {token for token in re.findall(r"[a-z]{4,}", behavior.lower()) if token not in {"caller", "payment", "after", "claim"}}
        if len(tokens) >= 2 and len(tokens.intersection(re.findall(r"[a-z]{4,}", lowered))) >= min(2, len(tokens)):
            forbidden_hits.append(behavior)
    words = re.findall(r"\S+", spoken)
    return {
        "schema_version": "deterministic-evaluation.v1",
        "case_id": case["case_id"],
        "word_count": len(words),
        "empty_response": not bool(spoken),
        "sensitive_request": sensitive_request,
        "unsupported_completion_claim": unsupported_completion,
        "redundant_confirmation": redundant_confirmation,
        "literal_forbidden_behavior_hits": forbidden_hits,
        "hard_gate_pass": not any((sensitive_request, unsupported_completion, redundant_confirmation, not spoken)),
    }
