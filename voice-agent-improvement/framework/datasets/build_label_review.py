"""Build the owner label-review payload for the 20 V12 discovery calls.

Gate 1 of the completion plan requires the project owner to convert Codex-assisted
provisional annotations into owner truth.  This module joins each preserved call
trace with its provisional label so the owner can review evidence and label side
by side, and emits a redacted payload for the standalone review app.

The provisional artifact is never mutated; the review app exports a new versioned
file which `ingest_owner_labels` turns into owner-reviewed references.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from framework.core.io import write_json

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts"
EMI = ARTIFACTS / "framework" / "emi"
CALLS = ARTIFACTS / "baseline" / "calls.jsonl"
PROVISIONAL = EMI / "reference_annotations.provisional.jsonl"
SELECTION = ROOT / "improvement" / "baseline_selection.json"
OUTPUT = EMI / "label_review" / "review_payload.json"

# Agent variables that are safe to surface as review context.  Contact fields are
# excluded even though the stored values are already masked.
CONTEXT_VARIABLES = (
    "userName",
    "productName",
    "merchantName",
    "outstandingAmount",
    "emiAmount",
    "emiNumber",
    "totalEmiCount",
    "dueDate",
    "daysPastDue",
    "lateChargeAmount",
    "disposition",
    "identityConfirmed",
    "promisedToPayDate",
    "callbackDateTime",
    "escalationReason",
    "userUpdatedNumber",
)

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
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _selection_index() -> dict[str, dict[str, Any]]:
    if not SELECTION.exists():
        return {}
    rows = json.loads(SELECTION.read_text(encoding="utf-8"))
    rows = rows.get("calls", rows) if isinstance(rows, dict) else rows
    return {row.get("run_id"): row for row in rows if isinstance(row, dict)}


def build(output: Path = OUTPUT) -> dict[str, Any]:
    labels = {row["trace_id"]: row for row in _read_jsonl(PROVISIONAL)}
    selection = _selection_index()

    records: list[dict[str, Any]] = []
    for call in _read_jsonl(CALLS):
        run_id = call["run_id"]
        annotation = labels.get(run_id, {})
        variables = call.get("attempt", {}).get("agent_variables", {})
        selected = selection.get(run_id, {})
        records.append(
            {
                "run_id": run_id,
                "corpus_role": call.get("corpus_role"),
                "benchmark_member": call.get("benchmark_member"),
                "primary_eligible": call.get("primary_eligible"),
                "expected_disposition": call.get("expected_disposition"),
                "observed_disposition": variables.get("disposition"),
                "scenario_note": selected.get("scenario") or selected.get("note"),
                "attempt": {
                    "duration_seconds": call.get("attempt", {}).get("duration_in_seconds"),
                    "ended_by": call.get("attempt", {}).get("ended_by"),
                    "failure_reason": call.get("attempt", {}).get("failure_reason"),
                    "language_name": call.get("attempt", {}).get("language_name"),
                    "average_agent_response_time_in_seconds": call.get("attempt", {}).get(
                        "average_agent_response_time_in_seconds"
                    ),
                    "num_messages": call.get("attempt", {}).get("num_messages"),
                },
                "context": {key: variables.get(key) for key in CONTEXT_VARIABLES if variables.get(key) is not None},
                "transcript": [
                    {
                        "turn_id": message.get("turn_id"),
                        "role": message.get("role"),
                        "content": message.get("content"),
                        "language_name": message.get("language_name"),
                    }
                    for message in call.get("messages", [])
                ],
                "provisional": {field: annotation.get("labels", {}).get(field) for field in REVIEW_FIELDS},
                "provisional_note": annotation.get("labels", {}).get("note"),
                "prompt_fixable": annotation.get("labels", {}).get("prompt_fixable"),
                "content_hash": annotation.get("content_hash"),
            }
        )

    records.sort(key=lambda row: row["run_id"])
    payload = {
        "schema_version": "label-review-payload.v1",
        "source_annotations": str(PROVISIONAL),
        "source_calls": str(CALLS),
        "review_fields": list(REVIEW_FIELDS),
        "instructions": (
            "For each call, read the transcript, then confirm or correct every provisional label. "
            "The exported file becomes owner-reviewed truth; the provisional artifact stays immutable."
        ),
        "records": records,
        "record_count": len(records),
    }
    write_json(output, payload)
    return payload


if __name__ == "__main__":
    result = build()
    print(f"{result['record_count']} calls written to {OUTPUT}")
