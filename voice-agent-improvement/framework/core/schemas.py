"""Validated, serializable contracts shared by every domain adapter."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping


ALLOWED_SPLITS = {"development", "regression", "held_out", "anchor_failure", "anchor_win"}
ALLOWED_REVIEW = {"provisional", "reviewed", "rejected"}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_hash(value: Mapping[str, Any]) -> str:
    unhashed = {key: item for key, item in value.items() if key != "content_hash"}
    return hashlib.sha256(canonical_json(unhashed).encode("utf-8")).hexdigest()


def _required(record: Mapping[str, Any], keys: tuple[str, ...], label: str) -> None:
    missing = [key for key in keys if record.get(key) in (None, "", [], {})]
    if missing:
        raise ValueError(f"{label} missing required fields: {', '.join(missing)}")


@dataclass(frozen=True)
class DomainPack:
    schema_version: str
    domain_id: str
    version: str
    display_name: str
    task_contract: dict[str, Any]
    environment_contract: dict[str, Any]
    tool_contract: dict[str, Any]
    policy_contract: dict[str, Any]
    outcome_contract: dict[str, Any]
    metric_contract: dict[str, Any]
    privacy_contract: dict[str, Any]
    deployment_contract: dict[str, Any]

    def __post_init__(self) -> None:
        _required(
            asdict(self),
            (
                "schema_version",
                "domain_id",
                "version",
                "display_name",
                "task_contract",
                "environment_contract",
                "policy_contract",
                "outcome_contract",
                "metric_contract",
            ),
            "domain pack",
        )
        _required(self.task_contract, ("primary_objective", "success_predicate", "accepted_terminal_states"), "task contract")
        _required(self.outcome_contract, ("observable_proxy", "unobservable_business_outcome"), "outcome contract")

    @classmethod
    def from_path(cls, path: Path) -> "DomainPack":
        return cls(**json.loads(path.read_text(encoding="utf-8")))

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["content_hash"] = content_hash(record)
        return record


@dataclass(frozen=True)
class CanonicalTrace:
    schema_version: str
    trace_id: str
    domain_id: str
    domain_pack_version: str
    source: dict[str, Any]
    context: dict[str, Any]
    turns: list[dict[str, Any]]
    observed_outcome: dict[str, Any]
    lineage: dict[str, Any]

    def __post_init__(self) -> None:
        _required(asdict(self), ("trace_id", "domain_id", "source", "turns", "lineage"), "canonical trace")
        for index, turn in enumerate(self.turns, start=1):
            _required(turn, ("turn_id", "actor", "content"), f"trace {self.trace_id} turn {index}")
            if turn["actor"] not in {"agent", "caller", "tool", "system"}:
                raise ValueError(f"invalid actor {turn['actor']!r} in trace {self.trace_id}")

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["content_hash"] = content_hash(record)
        return record


@dataclass(frozen=True)
class ReferenceAnnotation:
    schema_version: str
    trace_id: str
    review_status: str
    labels: dict[str, Any]
    provenance: dict[str, Any]

    def __post_init__(self) -> None:
        _required(asdict(self), ("trace_id", "review_status", "labels", "provenance"), "reference annotation")
        if self.review_status not in ALLOWED_REVIEW:
            raise ValueError(f"invalid review status {self.review_status!r}")

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["content_hash"] = content_hash(record)
        return record


@dataclass(frozen=True)
class EvaluationCase:
    schema_version: str
    case_id: str
    domain_id: str
    domain_pack_version: str
    failure_family: str
    test_type: str
    split: str
    language: str
    visible_agent_context: dict[str, Any]
    hidden_caller_state: dict[str, Any]
    environment_state: dict[str, Any]
    expected_transition: str
    accepted_terminal_states: list[str]
    forbidden_behaviors: list[str]
    exact_facts: dict[str, Any]
    lineage: dict[str, Any]
    reviewer_status: str = "provisional"
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _required(
            asdict(self),
            (
                "case_id",
                "domain_id",
                "failure_family",
                "test_type",
                "split",
                "language",
                "visible_agent_context",
                "hidden_caller_state",
                "expected_transition",
                "accepted_terminal_states",
                "lineage",
            ),
            "evaluation case",
        )
        if self.split not in ALLOWED_SPLITS:
            raise ValueError(f"invalid split {self.split!r}")
        if self.reviewer_status not in ALLOWED_REVIEW:
            raise ValueError(f"invalid reviewer status {self.reviewer_status!r}")
        leaked = set(self.hidden_caller_state).intersection(self.visible_agent_context)
        if leaked:
            raise ValueError(f"hidden caller state leaked into visible context keys: {sorted(leaked)}")

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["content_hash"] = content_hash(record)
        return record
