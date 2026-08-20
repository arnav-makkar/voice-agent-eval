"""Audit split independence and evidence eligibility for generated cases."""

from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path
from typing import Any

from framework.core.io import read_jsonl, write_json


ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "artifacts" / "framework" / "emi" / "datasets" / "emi_failure_derived_v3"
OUTPUT = DATASET / "integrity_audit.json"
SPLITS = ("development", "regression", "held_out", "anchor_failure", "anchor_win")


def _source_ids(rows: list[dict[str, Any]]) -> set[str]:
    return {
        str(row.get("lineage", {}).get("seed_trace_id"))
        for row in rows
        if row.get("lineage", {}).get("seed_trace_id")
    }


def _generator_requests(rows: list[dict[str, Any]]) -> set[str]:
    return {
        str(row.get("lineage", {}).get("generator_request_hash"))
        for row in rows
        if row.get("lineage", {}).get("generator_request_hash")
    }


def audit(dataset_dir: Path = DATASET, output: Path = OUTPUT) -> dict[str, Any]:
    rows = {split: read_jsonl(dataset_dir / f"{split}.jsonl") for split in SPLITS}
    source_sets = {split: _source_ids(items) for split, items in rows.items()}
    generator_sets = {split: _generator_requests(items) for split, items in rows.items()}
    overlaps: list[dict[str, Any]] = []
    for left, right in combinations(SPLITS, 2):
        shared_sources = sorted(source_sets[left].intersection(source_sets[right]))
        shared_requests = sorted(generator_sets[left].intersection(generator_sets[right]))
        overlaps.append(
            {
                "left": left,
                "right": right,
                "shared_source_trace_count": len(shared_sources),
                "shared_source_trace_ids": shared_sources,
                "shared_generator_request_count": len(shared_requests),
            }
        )

    critical_pairs = {
        ("development", "regression"),
        ("development", "held_out"),
        ("regression", "held_out"),
    }
    critical_overlap = [
        row
        for row in overlaps
        if (row["left"], row["right"]) in critical_pairs and row["shared_source_trace_count"] > 0
    ]
    record = {
        "schema_version": "dataset-integrity-audit.v1",
        "dataset_id": "emi_failure_derived_v3",
        "record_counts": {split: len(items) for split, items in rows.items()},
        "split_source_trace_counts": {split: len(values) for split, values in source_sets.items()},
        "overlaps": overlaps,
        "group_independence_pass": not critical_overlap,
        "legacy_held_out": {
            "access_status": "inspected_during_implementation_audit",
            "source_independence": "fail",
            "final_evidence_status": "compromised_development_only",
            "reason": (
                "The split shares source traces and generator batches with development/regression and was inspected. "
                "Its content hash proves immutability only; it is not a fresh final test."
            ),
        },
        "allowed_uses": [
            "development diagnostics",
            "challenge-library coverage",
            "regression debugging",
        ],
        "forbidden_claims": [
            "independent held-out evidence",
            "sealed or unopened final test",
            "voice-agent improvement proof",
        ],
        "required_replacement": (
            "Author a fresh group-separated multi-turn final test after evaluator and candidate methods freeze."
        ),
    }
    write_json(output, record)
    return record


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
