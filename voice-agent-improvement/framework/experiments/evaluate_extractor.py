"""Evaluate the output-extractor surface separately from the spoken prompt."""

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
CACHE = ROOT / "artifacts" / "framework" / "cache"
OUTPUT = ROOT / "artifacts" / "framework" / "emi" / "extractor"
BASE_CONTRACT = ROOT / "agent" / "v1" / "OUTPUT-VARIABLES.md"
PATCH = ROOT / "agent" / "candidates" / "gepa-v13" / "OUTPUT-VARIABLES.md"

ALLOWED = ["escalation", "alternate_number", "wrong_number", "dispute", "payment_ready", "ptp_today", "fptp", "callback", "rtp", "already_paid", "acknowledged", "call_disconnected"]
SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "extractions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "trace_id": {"type": "string"},
                    "disposition": {"type": "string", "enum": ALLOWED},
                    "call_summary": {"type": "string"},
                    "escalation_reason": {"type": "string"},
                    "unsupported_action_in_summary": {"type": "boolean"},
                    "evidence": {"type": "string"},
                },
                "required": ["trace_id", "disposition", "call_summary", "escalation_reason", "unsupported_action_in_summary", "evidence"],
            },
        }
    },
    "required": ["extractions"],
}


def evaluate(batch_size: int = 5, patch_path: Path = PATCH, candidate_id: str = "v13_patch", model: str = "gemini-pro-latest") -> dict[str, Any]:
    load_env_file(ROOT / ".env")
    traces = read_jsonl(TRACES)
    references = {row["trace_id"]: row for row in read_jsonl(REFERENCES)}
    contract = BASE_CONTRACT.read_text(encoding="utf-8") + "\n\n" + patch_path.read_text(encoding="utf-8")
    client = GeminiJsonClient(model=model, cache_dir=CACHE)
    results = []
    model_runs = []
    for start in range(0, len(traces), batch_size):
        batch = traces[start : start + batch_size]
        payload = [
            {
                "trace_id": trace["trace_id"],
                "turns": [{"actor": turn["actor"], "content": turn["content"]} for turn in trace["turns"]],
                "verified_tool_actions": [],
            }
            for trace in batch
        ]
        response = client.complete_json(
            system=contract + "\nApply the output contract independently to each supplied transcript. Return only structured extraction.",
            user=json.dumps({"traces": payload}, ensure_ascii=False),
            response_schema=SCHEMA,
            temperature=0,
            thinking_level="high",
            cache_namespace=f"extractor/{candidate_id}",
        )
        extracted = response.data.get("extractions", [])
        expected_ids = [trace["trace_id"] for trace in batch]
        if [row.get("trace_id") for row in extracted] != expected_ids:
            raise ValueError("extractor changed trace order")
        model_runs.append(response.metadata)
        for trace, row in zip(batch, extracted, strict=True):
            scenario_target = trace["context"]["expected_disposition"]
            labels = references[trace["trace_id"]]["labels"]
            if labels.get("primary_success"):
                expected = "payment_ready"
            elif labels.get("failure_category") in {"conditional_check_not_converted", "trust_resolution_missing_direct_close"}:
                expected = "acknowledged"
            else:
                expected = scenario_target
            platform = trace["observed_outcome"]["actual_disposition"]
            results.append(
                {
                    "trace_id": trace["trace_id"],
                    "expected_disposition": expected,
                    "scenario_target_disposition": scenario_target,
                    "platform_baseline_disposition": platform,
                    "candidate_extraction": row,
                    "platform_correct": platform == expected,
                    "candidate_correct": row["disposition"] == expected,
                }
            )
    total = len(results)
    summary = {
        "schema_version": "extractor-experiment.v1",
        "traces": total,
        "candidate_id": candidate_id,
        "patch_path": str(patch_path),
        "allowed_enum": ALLOWED,
        "platform_baseline_accuracy": round(sum(row["platform_correct"] for row in results) / total, 4),
        "candidate_accuracy": round(sum(row["candidate_correct"] for row in results) / total, 4),
        "candidate_unsupported_summary_rate": round(sum(row["candidate_extraction"]["unsupported_action_in_summary"] for row in results) / total, 4),
        "candidate_invalid_enum_count": sum(row["candidate_extraction"]["disposition"] not in ALLOWED for row in results),
        "disagreements": dict(collections.Counter(f"expected={row['expected_disposition']}|candidate={row['candidate_extraction']['disposition']}" for row in results if not row["candidate_correct"])),
        "judge_model": client.model,
        "reference_rule": "Provisional reference disposition uses observed human primary-success labels; conditional check/trust-without-commitment map to acknowledged rather than the scenario's desired payment_ready target.",
        "model_runs": model_runs,
        "claim_boundary": "Text re-extraction experiment on the 20 baseline transcripts; Indus production extractor and matched voice outputs remain separate gates.",
    }
    candidate_output = OUTPUT / candidate_id
    summary["details"] = write_jsonl(candidate_output / "details.jsonl", results)
    write_json(candidate_output / "summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--patch", type=Path, default=PATCH)
    parser.add_argument("--candidate-id", default="v13_patch")
    parser.add_argument("--model", default="gemini-pro-latest")
    args = parser.parse_args()
    print(json.dumps(evaluate(args.batch_size, args.patch, args.candidate_id, args.model), indent=2))


if __name__ == "__main__":
    main()
