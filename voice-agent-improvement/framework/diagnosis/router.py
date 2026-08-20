"""Route an observed failure to the smallest repair surface that can own it."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from framework.core.io import read_jsonl, write_json, write_jsonl


ROOT = Path(__file__).resolve().parents[2]
ANNOTATIONS = ROOT / "artifacts" / "framework" / "emi" / "reference_annotations.provisional.jsonl"
OUTPUT = ROOT / "artifacts" / "framework" / "emi" / "diagnosis"

ROUTES: dict[str, dict[str, Any]] = {
    "agent_prompt": {"primary_engine": "manual_prompt", "candidate_engines": ["manual_prompt", "gepa"], "isolation": "same model, tools, extractor and cases"},
    "output_extractor": {"primary_engine": "extractor_config", "candidate_engines": ["extractor_config", "judge_alignment"], "isolation": "frozen transcript, extractor-only diff"},
    "workflow": {"primary_engine": "workflow_config", "candidate_engines": ["workflow_config"], "isolation": "same prompt/model; state transition diff"},
    "tool": {"primary_engine": "tool_contract", "candidate_engines": ["tool_contract", "workflow_config"], "isolation": "recorded tool fixtures; no prompt mutation"},
    "knowledge": {"primary_engine": "knowledge_source", "candidate_engines": ["knowledge_source"], "isolation": "same policy; versioned knowledge diff"},
    "model": {"primary_engine": "model_or_runtime", "candidate_engines": ["model_or_runtime", "prompt_mitigation"], "isolation": "matched prompt, cases and decoding"},
    "evaluator": {"primary_engine": "evaluator_alignment", "candidate_engines": ["evaluator_alignment"], "isolation": "frozen responses and human references"},
    "channel": {"primary_engine": "voice_runtime", "candidate_engines": ["voice_runtime"], "isolation": "matched text intent; varied ASR/TTS/latency"},
    "policy": {"primary_engine": "human_policy_change", "candidate_engines": ["human_policy_change"], "isolation": "owner approval required before tests"},
    "mixed": {"primary_engine": "triage_ablation", "candidate_engines": ["manual_prompt", "workflow_config", "voice_runtime"], "isolation": "one component changed per arm"},
}


def route_failure(owner: str, prompt_fixable: bool | None = None) -> dict[str, Any]:
    route = dict(ROUTES.get(owner, ROUTES["mixed"]))
    if prompt_fixable is False:
        route["candidate_engines"] = [engine for engine in route["candidate_engines"] if engine not in {"manual_prompt", "gepa", "prompt_mitigation"}]
        if not route["candidate_engines"]:
            route["candidate_engines"] = [route["primary_engine"]]
    return {"owner": owner, **route}


def build(annotation_path: Path = ANNOTATIONS, output_dir: Path = OUTPUT) -> dict[str, Any]:
    episodes = []
    for row in read_jsonl(annotation_path):
        labels = row["labels"]
        if labels.get("failure_category") in {None, "", "none"}:
            continue
        route = route_failure(labels.get("failure_owner", "mixed"), labels.get("prompt_fixable"))
        episodes.append(
            {
                "schema_version": "failure-episode.v1",
                "trace_id": row["trace_id"],
                "review_status": row["review_status"],
                "failure_category": labels.get("failure_category", "none"),
                "first_breaking_turn": labels.get("first_breaking_turn"),
                "severity": labels.get("severity", "P3"),
                "evidence": labels.get("note", ""),
                "routing": route,
                "claim_boundary": "Routing is provisional until the source annotation receives owner review.",
            }
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = write_jsonl(output_dir / "failure_episodes.provisional.jsonl", episodes)
    owners = Counter(item["routing"]["owner"] for item in episodes)
    engines = Counter(item["routing"]["primary_engine"] for item in episodes)
    summary = {
        "schema_version": "diagnosis-summary.v1",
        "episodes": len(episodes),
        "review_status": "provisional",
        "owner_counts": dict(sorted(owners.items())),
        "primary_engine_counts": dict(sorted(engines.items())),
        "artifact": artifact,
        "method": "first observable breaking event + component owner + isolated repair route",
        "claim_boundary": "This routes failures; it does not prove the proposed repair will improve outcomes.",
    }
    write_json(output_dir / "summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", type=Path, default=ANNOTATIONS)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(json.dumps(build(args.annotations, args.output_dir), indent=2))


if __name__ == "__main__":
    main()
