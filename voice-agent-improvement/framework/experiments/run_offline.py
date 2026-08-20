"""Run candidate prompts against a fixed dataset without leaking hidden caller state."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from framework.adapters.gemini import GeminiJsonClient, load_env_file
from framework.core.io import read_jsonl, write_json, write_jsonl
from framework.core.schemas import canonical_json
from framework.evaluators.deterministic import evaluate_response
from framework.evaluators.semantic import judge_batch
from framework.experiments.tracking import log_experiment


ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "artifacts" / "framework" / "emi" / "datasets" / "emi_failure_derived_v3"
CACHE = ROOT / "artifacts" / "framework" / "cache"
EXPERIMENTS = ROOT / "artifacts" / "framework" / "emi" / "experiments"


AGENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "responses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string"},
                    "spoken_response": {"type": "string"},
                    "terminal_state": {"type": "string"},
                    "should_end_call": {"type": "boolean"},
                    "claimed_actions": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["case_id", "spoken_response", "terminal_state", "should_end_call", "claimed_actions"],
            },
        }
    },
    "required": ["responses"],
}


def _candidate_batch(client: GeminiJsonClient, candidate_prompt: str, cases: list[dict[str, Any]], candidate_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    visible_cases = [
        {
            "case_id": case["case_id"],
            "language": case["language"],
            "visible_agent_context": case["visible_agent_context"],
            "environment_state": {
                "official_app_available": case["environment_state"].get("official_app_available"),
                "verified_platform_actions": case["environment_state"].get("verified_platform_actions", []),
            },
            "exact_facts": case["exact_facts"],
        }
        for case in cases
    ]
    system = (
        candidate_prompt
        + "\n\nOFFLINE EVALUATION ADAPTER\n"
        + "Act independently on each supplied case. Hidden caller state is intentionally unavailable. "
        + "Return only the next spoken response and proposed terminal state. Do not narrate reasoning."
    )
    result = client.complete_json(
        system=system,
        user=json.dumps({"candidate_id": candidate_id, "cases": visible_cases}, ensure_ascii=False),
        response_schema=AGENT_SCHEMA,
        temperature=0,
        thinking_level="high",
        cache_namespace=f"candidate_responses/{candidate_id}",
    )
    responses = result.data.get("responses", [])
    expected = [case["case_id"] for case in cases]
    returned = [response.get("case_id") for response in responses]
    if returned != expected:
        raise ValueError(f"candidate response order mismatch: expected {expected}, got {returned}")
    return responses, result.metadata


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = max(len(rows), 1)
    semantic = [row["semantic"] for row in rows]
    deterministic = [row["deterministic"] for row in rows]
    return {
        "cases": len(rows),
        "task_success_rate": round(sum(row["task_success"] for row in semantic) / total, 4),
        "terminal_state_accuracy": round(sum(row["terminal_state_correct"] for row in semantic) / total, 4),
        "hard_safety_violation_rate": round(sum(row["hard_safety_violation"] for row in semantic) / total, 4),
        "integrity_violation_rate": round(sum(row["integrity_violation"] for row in semantic) / total, 4),
        "forbidden_behavior_rate": round(sum(row["forbidden_behavior_violation"] for row in semantic) / total, 4),
        "factual_error_rate": round(sum(row["factual_error"] for row in semantic) / total, 4),
        "redundant_confirmation_rate": round(sum(row["redundant_confirmation"] for row in deterministic) / total, 4),
        "average_directness": round(sum(row["directness_score"] for row in semantic) / total, 3),
        "average_quality": round(sum(row["conversation_quality_score"] for row in semantic) / total, 3),
        "failure_codes": dict(collections.Counter(row["failure_code"] for row in semantic if row["failure_code"] != "none")),
        "by_family": {
            family: {
                "cases": len(items),
                "task_success_rate": round(sum(item["semantic"]["task_success"] for item in items) / len(items), 4),
                "integrity_violation_rate": round(sum(item["semantic"]["integrity_violation"] for item in items) / len(items), 4),
            }
            for family in sorted({row["case"]["failure_family"] for row in rows})
            for items in [[row for row in rows if row["case"]["failure_family"] == family]]
        },
    }


def run_candidate(
    candidate_path: Path,
    candidate_id: str,
    splits: list[str],
    *,
    batch_size: int = 10,
    evaluator_version: str = "emi-semantic-pro-v2",
    agent_model: str = "gemini-3.6-flash",
    judge_model: str = "gemini-pro-latest",
) -> dict[str, Any]:
    load_env_file(ROOT / ".env")
    prompt = candidate_path.read_text(encoding="utf-8")
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    agent_client = GeminiJsonClient(model=agent_model, cache_dir=CACHE)
    judge_client = GeminiJsonClient(model=judge_model, cache_dir=CACHE)
    cases = [case for split in splits for case in read_jsonl(DATASET / f"{split}.jsonl")]
    output_rows = []
    model_runs = []
    for start in range(0, len(cases), batch_size):
        batch = cases[start : start + batch_size]
        responses, generation_meta = _candidate_batch(agent_client, prompt, batch, candidate_id)
        provisional = []
        for case, response in zip(batch, responses, strict=True):
            provisional.append({"case": case, "response": response, "deterministic": evaluate_response(case, response)})
        judgments, judge_meta = judge_batch(judge_client, provisional, evaluator_version=evaluator_version)
        for row, judgment in zip(provisional, judgments, strict=True):
            row["semantic"] = judgment
            output_rows.append(row)
        model_runs.append({"case_ids": [case["case_id"] for case in batch], "generation": generation_meta, "judge": judge_meta})

    summary = summarize(output_rows)
    experiment_id = f"{candidate_id}-{'-'.join(splits)}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    output_dir = EXPERIMENTS / experiment_id
    details_artifact = write_jsonl(output_dir / "case_results.jsonl", output_rows)
    metadata = {
        "schema_version": "offline-experiment.v1",
        "experiment_id": experiment_id,
        "candidate_id": candidate_id,
        "candidate_path": str(candidate_path),
        "candidate_prompt_sha256": prompt_hash,
        "dataset_id": "emi_failure_derived_v3",
        "splits": splits,
        "evaluator_version": evaluator_version,
        "agent_model": agent_client.model,
        "judge_model": judge_client.model,
        "summary": summary,
        "model_runs": model_runs,
        "details_artifact": details_artifact,
    }
    write_json(output_dir / "summary.json", metadata)
    metadata["mlflow"] = log_experiment(metadata, output_dir)
    write_json(output_dir / "summary.json", metadata)
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--splits", nargs="+", default=["development", "regression", "anchor_failure", "anchor_win"])
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--agent-model", default="gemini-3.6-flash")
    parser.add_argument("--judge-model", default="gemini-pro-latest")
    args = parser.parse_args()
    print(json.dumps(run_candidate(args.candidate, args.candidate_id, args.splits, batch_size=args.batch_size, agent_model=args.agent_model, judge_model=args.judge_model), indent=2))


if __name__ == "__main__":
    main()
