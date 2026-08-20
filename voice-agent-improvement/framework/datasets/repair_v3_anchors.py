"""Repair V3 preserved-win anchors to target the final agent decision point."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from framework.core.io import manifest, read_jsonl, write_json, write_jsonl
from framework.core.schemas import content_hash
from framework.datasets.derive_emi import FAMILIES, _anchor_case, validate_dataset
from framework.domain import load_domain_pack


ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "artifacts" / "framework" / "emi" / "datasets" / "emi_failure_derived_v3"
TRACES = ROOT / "artifacts" / "framework" / "emi" / "traces.jsonl"
REFERENCES = ROOT / "artifacts" / "framework" / "emi" / "reference_annotations.provisional.jsonl"
SPLITS = ("development", "regression", "held_out", "anchor_failure", "anchor_win")


def _artifact(path: Path, records: int | None = None) -> dict[str, Any]:
    body = path.read_bytes()
    result = {"path": str(path), "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
    if records is not None:
        result["records"] = records
    return result


def repair() -> dict[str, Any]:
    pack = load_domain_pack("emi_recovery")
    traces = {row["trace_id"]: row for row in read_jsonl(TRACES)}
    refs = {row["trace_id"]: row for row in read_jsonl(REFERENCES)}
    failures = [(key, row) for key, row in refs.items() if row["labels"].get("failure_category") != "none"]
    wins = [(key, row) for key, row in refs.items() if row["labels"].get("failure_category") == "none"]
    anchors = []
    for split, items in (("anchor_failure", failures), ("anchor_win", wins)):
        for index, (trace_id, reference) in enumerate(sorted(items), start=1):
            family = next((name for name, item in FAMILIES.items() if trace_id in item["seeds"]), "factual_outcome_integrity")
            row = _anchor_case(traces[trace_id], reference, family, split, index).to_record()
            row["domain_pack_version"] = pack.version
            row["accepted_terminal_states"] = FAMILIES[family]["accepted_terminal_states"]
            row["lineage"]["anchor_decision_point_repair"] = {
                "version": "v1",
                "rule": "latest_caller_utterance is the final caller turn before the target agent decision; agent closing text is never presented as caller input.",
            }
            row["content_hash"] = content_hash(row)
            anchors.append(row)
    failure_artifact = write_jsonl(DATASET / "anchor_failure.jsonl", [row for row in anchors if row["split"] == "anchor_failure"])
    win_artifact = write_jsonl(DATASET / "anchor_win.jsonl", [row for row in anchors if row["split"] == "anchor_win"])
    all_rows = [row for split in SPLITS for row in read_jsonl(DATASET / f"{split}.jsonl")]
    validation = validate_dataset(all_rows)
    validation_artifact = write_json(DATASET / "validation.json", validation)
    held_out = _artifact(DATASET / "held_out.jsonl", 30)
    artifacts = [
        _artifact(DATASET / "development.jsonl", 120),
        _artifact(DATASET / "regression.jsonl", 30),
        held_out,
        failure_artifact,
        win_artifact,
        validation_artifact,
    ]
    stage = manifest(
        "repair_anchor_decision_points",
        artifacts,
        dataset_id="emi_failure_derived_v3",
        domain_pack_version=pack.version,
        held_out_seal_sha256=held_out["sha256"],
        held_out_changed=False,
        repaired_failure_anchors=15,
        repaired_win_anchors=5,
        reference_status="provisional",
    )
    write_json(DATASET / "manifest.json", stage)
    return stage


if __name__ == "__main__":
    print(json.dumps(repair(), indent=2))
