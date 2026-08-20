"""Project-owned evaluation contracts inspired by EVA and tau, not tied to a provider."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def record_hash(value: Any) -> str:
    record = asdict(value) if hasattr(value, "__dataclass_fields__") else value
    return hashlib.sha256(canonical_json(record).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class UserStep:
    text: str
    intent: str
    notes: str = ""


@dataclass(frozen=True)
class EvaluationScenario:
    schema_version: str
    scenario_id: str
    domain_id: str
    split: str
    source_group: str
    failure_family: str
    language: str
    user_goal: str
    persona: dict[str, Any]
    visible_context: dict[str, Any]
    hidden_state: dict[str, Any]
    initial_environment: dict[str, Any]
    user_steps: list[UserStep]
    accepted_dispositions: list[str]
    expected_state: dict[str, Any]
    required_actions: list[dict[str, Any]] = field(default_factory=list)
    communication_assertions: list[str] = field(default_factory=list)
    forbidden_phrases: list[str] = field(default_factory=list)
    perturbations: list[str] = field(default_factory=list)
    max_agent_turns: int = 6
    reviewer_status: str = "reviewed"

    def __post_init__(self) -> None:
        if not self.scenario_id or not self.source_group or not self.user_steps:
            raise ValueError("scenario_id, source_group, and user_steps are required")
        if self.split not in {"development", "validation", "regression", "fresh_final"}:
            raise ValueError(f"unsupported split: {self.split}")
        overlap = set(self.hidden_state).intersection(self.visible_context)
        if overlap:
            raise ValueError(f"hidden state leaked into visible context: {sorted(overlap)}")
        if self.max_agent_turns < 1:
            raise ValueError("max_agent_turns must be positive")

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "EvaluationScenario":
        prepared = dict(record)
        prepared.pop("content_hash", None)
        prepared["user_steps"] = [UserStep(**item) for item in prepared["user_steps"]]
        return cls(**prepared)

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["content_hash"] = record_hash(record)
        return record


@dataclass(frozen=True)
class ToolEvent:
    sequence: int
    name: str
    arguments: dict[str, Any]
    result: dict[str, Any]
    status: str
    latency_ms: float = 0.0


@dataclass(frozen=True)
class ConversationTurn:
    sequence: int
    actor: str
    content: str
    latency_ms: float | None = None


@dataclass
class ScenarioRun:
    schema_version: str
    run_id: str
    scenario_id: str
    candidate_id: str
    candidate_hash: str
    adapter: str
    started_at: str
    ended_at: str
    termination_reason: str
    interaction_id: str | None
    turns: list[ConversationTurn]
    tool_events: list[ToolEvent]
    initial_state: dict[str, Any]
    final_state: dict[str, Any]
    agent_declared_disposition: str
    simulator_validation: dict[str, Any]
    provenance: dict[str, Any]

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "ScenarioRun":
        prepared = dict(record)
        prepared.pop("content_hash", None)
        prepared["turns"] = [ConversationTurn(**item) for item in prepared["turns"]]
        prepared["tool_events"] = [ToolEvent(**item) for item in prepared["tool_events"]]
        return cls(**prepared)

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["content_hash"] = record_hash(record)
        return record
