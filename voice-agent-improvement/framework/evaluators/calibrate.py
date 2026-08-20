"""Measure evaluator agreement against the 20 provisional baseline annotations."""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
from typing import Any

from framework.adapters.gemini import GeminiJsonClient, load_env_file
from framework.core.io import read_jsonl, write_json, write_jsonl


ROOT = Path(__file__).resolve().parents[2]
TRACES = ROOT / "artifacts" / "framework" / "emi" / "traces.jsonl"
REFERENCES = ROOT / "artifacts" / "framework" / "emi" / "reference_annotations.provisional.jsonl"
OUTPUT = ROOT / "artifacts" / "framework" / "emi" / "evaluator_calibration"
CACHE = ROOT / "artifacts" / "framework" / "cache"


SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "evaluations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "trace_id": {"type": "string"},
                    "task_success": {"type": "boolean"},
                    "primary_success": {"type": "boolean"},
                    "first_breaking_turn": {"type": ["integer", "null"]},
                    "failure_category": {"type": "string"},
                    "failure_owner": {"type": "string"},
                    "hard_safety_violation": {"type": "boolean"},
                    "integrity_violation": {"type": "boolean"},
                    "evidence": {"type": "string"},
                },
                "required": ["trace_id", "task_success", "primary_success", "first_breaking_turn", "failure_category", "failure_owner", "hard_safety_violation", "integrity_violation", "evidence"],
            },
        }
    },
    "required": ["evaluations"],
}


def _agreement(prediction: dict[str, Any], reference: dict[str, Any]) -> dict[str, Any]:
    labels = reference["labels"]
    predicted_turn = prediction.get("first_breaking_turn")
    reference_turn = labels.get("first_breaking_turn")
    turn_match = predicted_turn == reference_turn or (
        predicted_turn is not None and reference_turn is not None and abs(int(predicted_turn) - int(reference_turn)) <= 1
    )
    return {
        key: prediction.get(key) == labels.get(key)
        for key in ("task_success", "primary_success", "failure_category", "failure_owner", "hard_safety_violation", "integrity_violation")
    } | {"first_breaking_turn_within_one": turn_match}


def calibrate(
    batch_size: int = 5,
    model: str = "gemini-pro-latest",
    references: Path = REFERENCES,
    output: Path | None = None,
) -> dict[str, Any]:
    load_env_file(ROOT / ".env")
    output = output or OUTPUT
    traces = read_jsonl(TRACES)
    ref_rows = read_jsonl(references)
    refs = {row["trace_id"]: row for row in ref_rows}
    reference_status = ref_rows[0].get("review_status", "provisional") if ref_rows else "provisional"
    review_mode = (ref_rows[0].get("provenance", {}) or {}).get("review_mode") if ref_rows else None
    client = GeminiJsonClient(model=model, cache_dir=CACHE)
    results = []
    calls = []
    system = (
        "You are calibrating a voice-agent evaluator. Read each real transcript independently. "
        "An explicit agreement to pay now is primary success; agreement to check or try is not. "
        "Task success can include correct safe handling of dispute, fraud, refusal, callback, or already-paid states. "
        "The first breaking turn is the earliest observable agent or extractor turn that causes failure. "
        "Integrity means no unsupported payment completion, account update, or stronger future certainty. "
        "Use failure_category='none', failure_owner='none', and null turn for a clean trace."
    )
    for start in range(0, len(traces), batch_size):
        batch = traces[start : start + batch_size]
        payload = [
            {
                "trace_id": trace["trace_id"],
                "primary_eligible": trace["context"]["primary_eligible"],
                "expected_disposition": trace["context"]["expected_disposition"],
                "observed_disposition": trace["observed_outcome"]["actual_disposition"],
                "call_summary": trace["observed_outcome"]["call_summary"],
                "turns": [{"turn_id": row["turn_id"], "actor": row["actor"], "content": row["content"]} for row in trace["turns"]],
            }
            for trace in batch
        ]
        result = client.complete_json(
            system=system,
            user=json.dumps({"traces": payload}, ensure_ascii=False),
            response_schema=SCHEMA,
            temperature=0,
            thinking_level="high",
            cache_namespace="evaluator_calibration/emi_semantic_pro_v2",
        )
        predictions = result.data.get("evaluations", [])
        expected = [row["trace_id"] for row in batch]
        if [row.get("trace_id") for row in predictions] != expected:
            raise ValueError("calibration evaluator changed trace order")
        calls.append(result.metadata)
        for prediction in predictions:
            trace_id = prediction["trace_id"]
            results.append(
                {
                    "trace_id": trace_id,
                    "prediction": prediction,
                    "reference": refs[trace_id]["labels"],
                    "provisional_reference": refs[trace_id]["labels"],
                    "agreement": _agreement(prediction, refs[trace_id]),
                }
            )
    metric_names = list(results[0]["agreement"])
    agreement = {name: round(sum(row["agreement"][name] for row in results) / len(results), 4) for name in metric_names}
    confusion = {
        field: dict(
            collections.Counter(
                f"reference={row['provisional_reference'].get(field)}|prediction={row['prediction'].get(field)}"
                for row in results
            )
        )
        for field in ("task_success", "primary_success", "integrity_violation", "failure_category")
    }
    details = write_jsonl(output / "details.jsonl", results)
    owner_reviewed = reference_status == "owner_reviewed"
    if owner_reviewed:
        interpretation = (
            "Agreement is measured against owner-reviewed reference labels"
            + (f" ({review_mode})" if review_mode else "")
            + ". Because the owner confirmed the references rather than correcting them, the weak diagnostic "
            "agreement is attributable to the evaluator rather than to label noise, and becomes an evaluator "
            "repair target rather than an open question."
        )
    else:
        interpretation = (
            "Agreement measures consistency with Codex-assisted provisional labels. It is not independent "
            "human validation until the owner reviews the references."
        )
    summary = {
        "schema_version": "evaluator-calibration.v1",
        "evaluator_version": "emi-semantic-pro-v2",
        "judge_model": client.model,
        "reference_status": reference_status,
        "reference_path": str(references),
        "review_mode": review_mode,
        "calls": len(results),
        "agreement": agreement,
        "confusion": confusion,
        "model_runs": calls,
        "details": details,
        "interpretation": interpretation,
    }
    write_json(output / "summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--model", default="gemini-pro-latest")
    parser.add_argument("--references", type=Path, default=REFERENCES)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    print(json.dumps(calibrate(args.batch_size, args.model, args.references, args.output), indent=2))


if __name__ == "__main__":
    main()
