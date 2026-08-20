"""Typed repair-engine registry; optimization is only one engine class."""

from __future__ import annotations

from typing import Any


ENGINES: dict[str, dict[str, Any]] = {
    "manual_prompt": {"surface": "prompt", "automated": False, "runner": "framework.experiments.run_offline", "required_gate": "paired prompt ablation"},
    "gepa": {"surface": "prompt", "automated": True, "runner": "framework.experiments.run_gepa", "required_gate": "regression + fresh group-separated final test + human diff"},
    "extractor_config": {"surface": "output_extractor", "automated": False, "runner": "framework.experiments.evaluate_extractor", "required_gate": "frozen transcript re-extraction"},
    "judge_alignment": {"surface": "evaluator", "automated": False, "runner": "framework.evaluators.calibrate", "required_gate": "human agreement threshold"},
    "workflow_config": {"surface": "state_machine", "automated": False, "runner": None, "required_gate": "transition fixtures + provider preview"},
    "tool_contract": {"surface": "tools", "automated": False, "runner": None, "required_gate": "sandbox tool fixtures + idempotency"},
    "knowledge_source": {"surface": "knowledge", "automated": False, "runner": None, "required_gate": "citation and freshness checks"},
    "model_or_runtime": {"surface": "model", "automated": False, "runner": None, "required_gate": "matched model ablation"},
    "voice_runtime": {"surface": "channel", "automated": False, "runner": None, "required_gate": "matched voice transfer tests"},
    "human_policy_change": {"surface": "policy", "automated": False, "runner": None, "required_gate": "named policy-owner approval"},
    "triage_ablation": {"surface": "mixed", "automated": False, "runner": None, "required_gate": "one-variable-at-a-time ablation"},
}


def repair_engine(engine_id: str) -> dict[str, Any]:
    if engine_id not in ENGINES:
        raise KeyError(f"unknown repair engine {engine_id!r}; available: {', '.join(sorted(ENGINES))}")
    return {"engine_id": engine_id, **ENGINES[engine_id]}


def list_repair_engines() -> list[dict[str, Any]]:
    return [repair_engine(engine_id) for engine_id in sorted(ENGINES)]
