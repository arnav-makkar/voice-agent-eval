"""Audit scenario/transcript JSONL before any metric or optimizer consumes it."""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
from typing import Any

from dataset.simulation import canonical_sha256


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def audit_scenarios(scenarios: list[dict[str, Any]]) -> tuple[list[str], dict[str, Any]]:
    issues: list[str] = []
    ids = [item.get("scenario_id") for item in scenarios]
    if len(ids) != len(set(ids)):
        issues.append("duplicate scenario_id")
    for item in scenarios:
        expected_hash = item.get("contract_sha256")
        unhashed = {key: value for key, value in item.items() if key != "contract_sha256"}
        if expected_hash != canonical_sha256(unhashed):
            issues.append(f"hash mismatch: {item.get('scenario_id')}")
        inputs = item.get("public_environment", {}).get("runtime_inputs", {})
        if inputs.get("productName") != "Samsung 55-inch 4K Smart TV":
            issues.append(f"non-TV product: {item.get('scenario_id')}")
        try:
            if int(inputs["outstandingAmount"]) != int(inputs["emiAmount"]) + int(inputs["lateChargeAmount"]):
                issues.append(f"ledger arithmetic mismatch: {item.get('scenario_id')}")
        except (KeyError, TypeError, ValueError):
            issues.append(f"invalid ledger fields: {item.get('scenario_id')}")
    split_counts = collections.Counter(item.get("split") for item in scenarios)
    if len(scenarios) == 150 and split_counts != {"development": 90, "regression": 30, "held_out": 30}:
        issues.append(f"unexpected full-manifest split counts: {dict(split_counts)}")
    return issues, {
        "scenario_count": len(scenarios),
        "split_counts": dict(split_counts),
        "intent_counts": dict(collections.Counter(
            item.get("private_user_state", {}).get("intent") for item in scenarios
        )),
    }


def audit_transcripts(
    transcripts: list[dict[str, Any]],
    scenarios_by_id: dict[str, dict[str, Any]],
) -> tuple[list[str], dict[str, Any]]:
    issues: list[str] = []
    transcript_ids = [item.get("transcript_id") for item in transcripts]
    if len(transcript_ids) != len(set(transcript_ids)):
        issues.append("duplicate transcript_id")
    for item in transcripts:
        scenario_id = item.get("scenario_id")
        scenario = scenarios_by_id.get(scenario_id)
        if scenario is None:
            issues.append(f"unknown scenario_id in transcript: {scenario_id}")
            continue
        if item.get("scenario_contract_sha256") != scenario.get("contract_sha256"):
            issues.append(f"scenario hash mismatch in transcript: {item.get('transcript_id')}")
        turns = item.get("turns", [])
        if len(turns) < 2 or turns[0].get("speaker") != "agent":
            issues.append(f"invalid opening turns: {item.get('transcript_id')}")
            continue
        for index, turn in enumerate(turns):
            expected = "agent" if index % 2 == 0 else "user"
            if turn.get("turn_index") != index or turn.get("speaker") != expected or not str(turn.get("text", "")).strip():
                issues.append(f"invalid turn sequence: {item.get('transcript_id')} at {index}")
                break
    modes = collections.Counter(item.get("generation", {}).get("mode") for item in transcripts)
    evidentiary = sum(bool(item.get("generation", {}).get("benchmark_evidence")) for item in transcripts)
    return issues, {
        "transcript_count": len(transcripts),
        "generation_modes": dict(modes),
        "benchmark_evidence_count": evidentiary,
        "non_evidentiary_count": len(transcripts) - evidentiary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", type=Path, default=Path(__file__).with_name("scenarios-v2.jsonl"))
    parser.add_argument("--transcripts", type=Path)
    args = parser.parse_args()

    scenarios = read_jsonl(args.scenarios)
    issues, summary = audit_scenarios(scenarios)
    if args.transcripts:
        transcript_issues, transcript_summary = audit_transcripts(
            read_jsonl(args.transcripts), {item["scenario_id"]: item for item in scenarios}
        )
        issues.extend(transcript_issues)
        summary.update(transcript_summary)
    summary["status"] = "pass" if not issues else "fail"
    summary["issues"] = issues
    print(json.dumps(summary, indent=2, sort_keys=True))
    if issues:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
