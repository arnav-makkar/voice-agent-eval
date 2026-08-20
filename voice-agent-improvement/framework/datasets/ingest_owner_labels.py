"""Convert an owner label-review export into versioned owner-reviewed references.

The provisional artifact is immutable evidence and is never edited.  This module
writes a new versioned file alongside it and records which labels the owner
changed, so evaluator calibration can be re-reported against owner truth while
the original Codex-assisted labels remain auditable.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from framework.core.io import write_json

ROOT = Path(__file__).resolve().parents[2]
EMI = ROOT / "artifacts" / "framework" / "emi"
PROVISIONAL = EMI / "reference_annotations.provisional.jsonl"
REVIEW_FIELDS = (
    "primary_success",
    "task_success",
    "first_breaking_turn",
    "failure_category",
    "failure_owner",
    "severity",
    "integrity_violation",
    "hard_safety_violation",
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def confirm_all_from_provisional(attested_by: str) -> dict[str, Any]:
    """Build an export in which the owner confirms every provisional label unchanged.

    Bulk confirmation is a legitimate owner action, but it is not the same evidence
    as twenty independent per-call adjudications.  The distinction is recorded in
    `review_mode` so downstream reporting can describe it accurately.
    """
    return {
        "schema_version": "owner-label-export.v1",
        "review_mode": "bulk_confirmation",
        "attested_by": attested_by,
        "records": [
            {
                "trace_id": row["trace_id"],
                "review_status": "owner_reviewed",
                "labels": {field: row["labels"].get(field) for field in REVIEW_FIELDS},
                "owner_comment": "Confirmed unchanged by the project owner.",
                "provisional_content_hash": row.get("content_hash"),
                "changed_fields": [],
            }
            for row in _read_jsonl(PROVISIONAL)
        ],
    }


def ingest(export_path: Path | None = None, version: str = "v1", export: dict[str, Any] | None = None) -> dict[str, Any]:
    if export is None:
        export = json.loads(export_path.read_text(encoding="utf-8"))
    provisional = {row["trace_id"]: row for row in _read_jsonl(PROVISIONAL)}

    reviewed = [row for row in export.get("records", []) if row.get("review_status") == "owner_reviewed"]
    if len(reviewed) != len(provisional):
        missing = sorted(set(provisional) - {row["trace_id"] for row in reviewed})
        raise SystemExit(
            f"Refusing to publish partial owner truth: {len(reviewed)}/{len(provisional)} reviewed. Missing: {missing}"
        )

    out_path = EMI / f"reference_annotations.owner_reviewed.{version}.jsonl"
    changes: list[dict[str, Any]] = []
    lines: list[str] = []

    for row in sorted(reviewed, key=lambda item: item["trace_id"]):
        trace_id = row["trace_id"]
        source = provisional[trace_id]
        labels = {field: row["labels"].get(field) for field in REVIEW_FIELDS}
        changed = [field for field in REVIEW_FIELDS if labels[field] != source["labels"].get(field)]
        if changed:
            changes.append(
                {
                    "trace_id": trace_id,
                    "fields": changed,
                    "before": {field: source["labels"].get(field) for field in changed},
                    "after": {field: labels[field] for field in changed},
                }
            )
        lines.append(
            json.dumps(
                {
                    "trace_id": trace_id,
                    "schema_version": "reference-annotation.v2",
                    "review_status": "owner_reviewed",
                    "labels": labels,
                    "owner_comment": row.get("owner_comment", ""),
                    "provenance": {
                        "annotator": "project_owner",
                        "independent_human_review": True,
                        "review_mode": export.get("review_mode", "per_call_review"),
                        "attested_by": export.get("attested_by"),
                        "supersedes": str(PROVISIONAL),
                        "provisional_content_hash": source.get("content_hash"),
                        "changed_from_provisional": changed,
                    },
                },
                sort_keys=True,
            )
        )

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary = {
        "schema_version": "owner-label-ingest.v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "version": version,
        "review_mode": export.get("review_mode", "per_call_review"),
        "attested_by": export.get("attested_by"),
        "source_export": str(export_path) if export_path else "generated:confirm_all_from_provisional",
        "owner_reviewed_path": str(out_path),
        "records": len(lines),
        "records_changed": len(changes),
        "records_confirmed": len(lines) - len(changes),
        "changes": changes,
        "claim_boundary": (
            "Owner-reviewed labels supersede the Codex-assisted provisional set for calibration reporting. "
            "The provisional artifact remains immutable evidence."
        ),
    }
    write_json(EMI / "evaluator_calibration" / f"owner_review_{version}.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", type=Path, nargs="?", help="owner_labels_export.json downloaded from the review app")
    parser.add_argument("--version", default="v1")
    parser.add_argument(
        "--confirm-all-from-provisional",
        metavar="ATTESTED_BY",
        help="Owner confirms every provisional label unchanged; recorded as review_mode=bulk_confirmation.",
    )
    args = parser.parse_args()
    if args.confirm_all_from_provisional:
        summary = ingest(None, args.version, export=confirm_all_from_provisional(args.confirm_all_from_provisional))
    elif args.export:
        summary = ingest(args.export, args.version)
    else:
        raise SystemExit("Provide an export file or --confirm-all-from-provisional ATTESTED_BY")
    print(
        f"{summary['records']} owner-reviewed labels written "
        f"({summary['records_confirmed']} confirmed, {summary['records_changed']} corrected)\n"
        f"-> {summary['owner_reviewed_path']}"
    )


if __name__ == "__main__":
    main()
