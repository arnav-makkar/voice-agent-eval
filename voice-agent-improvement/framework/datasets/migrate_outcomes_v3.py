"""Migrate valid V2 dialogue cases to the exact Indus outcome vocabulary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from framework.core.io import manifest, read_jsonl, write_json, write_jsonl
from framework.core.schemas import content_hash
from framework.datasets.derive_emi import FAMILIES, validate_dataset
from framework.domain import load_domain_pack


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "artifacts" / "framework" / "emi" / "datasets" / "emi_failure_derived_v2"
OUTPUT = ROOT / "artifacts" / "framework" / "emi" / "datasets" / "emi_failure_derived_v3"
SPLITS = ("development", "regression", "held_out", "anchor_failure", "anchor_win")


def migrate(source: Path = SOURCE, output: Path = OUTPUT) -> dict[str, Any]:
    pack = load_domain_pack("emi_recovery")
    source_manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    records = []
    for split in SPLITS:
        for row in read_jsonl(source / f"{split}.jsonl"):
            original_hash = row["content_hash"]
            family = row["failure_family"]
            row["domain_pack_version"] = pack.version
            row["accepted_terminal_states"] = FAMILIES[family]["accepted_terminal_states"]
            row["lineage"] = {
                **row["lineage"],
                "outcome_vocabulary_migration": {
                    "from_dataset": "emi_failure_derived_v2",
                    "source_content_hash": original_hash,
                    "reason": "Map generic framework outcomes to the deployed Indus enum without changing generated dialogue content.",
                    "mapping": {"promise_to_pay": "fptp", "refusal": "rtp", "wrong_party": "wrong_number"},
                },
            }
            row["content_hash"] = content_hash(row)
            records.append(row)
    validation = validate_dataset(records)
    artifacts = []
    for split in SPLITS:
        artifacts.append(write_jsonl(output / f"{split}.jsonl", [row for row in records if row["split"] == split]))
    artifacts.append(write_json(output / "validation.json", validation))
    held_out_hash = next(item["sha256"] for item in artifacts if item["path"].endswith("held_out.jsonl"))
    stage = manifest(
        "migrate_outcome_vocabulary",
        artifacts,
        dataset_id="emi_failure_derived_v3",
        source_dataset_id="emi_failure_derived_v2",
        source_manifest_sha256=hashlib.sha256((source / "manifest.json").read_bytes()).hexdigest(),
        source_held_out_seal_sha256=source_manifest["metadata"]["held_out_seal_sha256"],
        held_out_seal_sha256=held_out_hash,
        domain_pack_hash=pack.to_record()["content_hash"],
        domain_pack_version=pack.version,
        dialogue_content_regenerated=False,
        outcome_mapping={"promise_to_pay": "fptp", "refusal": "rtp", "wrong_party": "wrong_number"},
        reference_status="provisional",
    )
    write_json(output / "manifest.json", stage)
    write_json(
        source / "semantic_audit.json",
        {
            "schema_version": "dataset-semantic-audit.v1",
            "status": "invalidated_for_scoring",
            "dataset_id": "emi_failure_derived_v2",
            "content_valid": True,
            "usable_for_experiments": False,
            "reason": "Accepted terminal states used generic framework names rather than the deployed Indus enum.",
            "superseded_by": "emi_failure_derived_v3",
        },
    )
    return stage


if __name__ == "__main__":
    print(json.dumps(migrate(), indent=2))
