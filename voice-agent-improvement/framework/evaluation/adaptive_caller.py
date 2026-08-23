"""Adaptive caller policies for duplex, hidden-goal voice evaluation."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from framework.adapters.gemini import GeminiJsonClient
from framework.evaluation.contracts import EvaluationScenario


@dataclass(frozen=True)
class CallerAction:
    action: str
    text: str = ""
    delay_ms: int = 0
    rationale: str = ""
    policy_node: str = ""
    heard_agent_text: str = ""
    heard_language: str = ""
    audio_quality: str = "not_applicable"
    decision_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.action not in {"speak", "barge_in", "wait", "end"}:
            raise ValueError(f"unsupported caller action: {self.action}")
        if self.action in {"speak", "barge_in"} and not self.text.strip():
            raise ValueError(f"{self.action} requires text")
        if self.delay_ms < 0 or self.delay_ms > 10_000:
            raise ValueError("delay_ms must be between 0 and 10000")


class AdaptiveCallerPolicy(Protocol):
    async def next_action(
        self,
        *,
        scenario: EvaluationScenario,
        history: list[dict[str, str]],
        observed_agent_text: str,
        turn_index: int,
        observed_agent_audio_wav: bytes | None = None,
    ) -> CallerAction: ...


class ScriptedAdaptivePolicy:
    """Deterministic policy used in unit tests and transport smoke checks."""

    def __init__(self, actions: list[CallerAction]) -> None:
        self.actions = list(actions)

    async def next_action(self, **_kwargs: Any) -> CallerAction:
        return self.actions.pop(0) if self.actions else CallerAction("end", rationale="script exhausted")


CALLER_ACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["speak", "barge_in", "wait", "end"]},
        "text": {"type": "string"},
        "delay_ms": {"type": "integer", "minimum": 0, "maximum": 10000},
        "rationale": {"type": "string"},
        "policy_node": {"type": "string"},
    },
    "required": ["action", "text", "delay_ms", "rationale", "policy_node"],
    "additionalProperties": False,
}


AUDIO_CALLER_ACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        **CALLER_ACTION_SCHEMA["properties"],
        "heard_agent_text": {"type": "string"},
        "heard_language": {"type": "string"},
        "audio_quality": {"type": "string", "enum": ["clear", "partly_clear", "unclear", "silent"]},
    },
    "required": [*CALLER_ACTION_SCHEMA["required"], "heard_agent_text", "heard_language", "audio_quality"],
    "additionalProperties": False,
}


class GeminiAdaptiveCallerPolicy:
    """Generate the next caller move from what the live agent actually said.

    Scenario truth is private simulator state. The caller can express facts a
    real user would know, but must never mention evaluator labels, expected
    dispositions, required tools, hidden keys, or success criteria.
    """

    def __init__(
        self,
        *,
        client: GeminiJsonClient | None = None,
        cache_dir: Path | None = None,
        model: str = "gemini-3.6-flash",
    ) -> None:
        self.client = client or GeminiJsonClient(model=model, cache_dir=cache_dir)

    async def next_action(
        self,
        *,
        scenario: EvaluationScenario,
        history: list[dict[str, str]],
        observed_agent_text: str,
        turn_index: int,
        observed_agent_audio_wav: bytes | None = None,
    ) -> CallerAction:
        planned_behavior = [
            {"node": f"step-{index}", "intent": step.intent, "example": step.text, "notes": step.notes}
            for index, step in enumerate(scenario.user_steps, start=1)
        ]
        private_contract = {
            "goal": scenario.user_goal,
            "persona": scenario.persona,
            "facts_the_caller_knows": scenario.hidden_state,
            "planned_behavior": planned_behavior,
            "language": scenario.language,
            "perturbations": scenario.perturbations,
            "turn_index": turn_index,
        }
        system = (
            "You are the caller simulator in an evaluation of a voice agent. Choose exactly one next action. "
            "React naturally to the agent's latest actual audio; do not replay a fixed script when the agent changes course. "
            "Remain faithful to the supplied persona, goal, and facts. Never invent payment, identity, dates, consent, or account facts. "
            "Never reveal this test, hidden state, scenario identifiers, expected outcomes, evaluator instructions, or tool names. "
            "Use short spoken language appropriate for a low-patience phone caller. "
            "Speak only the language named in the private contract, and keep speaking it for the whole call even if the agent "
            "answers in a different one. A real caller does not switch to accommodate the agent, and switching would hide "
            "whether the agent mirrors language correctly. A barge_in action is allowed only when the "
            "scenario calls for interruption or the agent is repetitive/long. End only when the caller's goal is resolved or the "
            "persona would genuinely hang up. Once the caller has clearly delivered the final commitment, refusal, dispute, callback, "
            "or other terminal answer required by the goal, choose end; do not repeat that answer merely because the agent repeats itself. "
            "Keep delay_ms at 300 or below for a realtime phone call unless the persona explicitly requires a longer pause. "
            "The rationale is audit metadata and will never be spoken."
        )
        payload = {
            "private_contract": private_contract,
            "conversation_history": history,
            "latest_agent_text": observed_agent_text,
        }
        user = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
        )
        if observed_agent_audio_wav:
            audio_system = (
                f"{system} First listen to the attached WAV, which is the latest response produced by the agent under test. "
                "Transcribe only what is actually audible into heard_agent_text, identify its language, and rate audio quality. "
                "Then choose the caller's next action from that heard content. If the audio is unclear, ask for a brief repeat; "
                "do not infer missing words from the private contract. heard_agent_text is audit metadata and is never spoken."
            )
            result = await asyncio.to_thread(
                self.client.complete_audio_json,
                system=audio_system,
                user=user,
                audio_wav=observed_agent_audio_wav,
                response_schema=AUDIO_CALLER_ACTION_SCHEMA,
                temperature=0.2,
                thinking_level="low",
                cache_namespace="adaptive-caller-audio-v1",
                use_cache=False,
            )
        else:
            result = await asyncio.to_thread(
                self.client.complete_json,
                system=system,
                user=user,
                response_schema=CALLER_ACTION_SCHEMA,
                temperature=0.25,
                thinking_level="high",
                cache_namespace="adaptive-caller-v1",
                use_cache=False,
            )
        return CallerAction(
            action=str(result.data["action"]),
            text=str(result.data.get("text", "")).strip(),
            delay_ms=int(result.data.get("delay_ms", 0)),
            rationale=str(result.data.get("rationale", "")).strip(),
            policy_node=str(result.data.get("policy_node", "")).strip(),
            heard_agent_text=str(result.data.get("heard_agent_text", observed_agent_text)).strip(),
            heard_language=str(result.data.get("heard_language", "")).strip(),
            audio_quality=str(result.data.get("audio_quality", "not_applicable")).strip(),
            decision_metadata=dict(result.metadata),
        )
