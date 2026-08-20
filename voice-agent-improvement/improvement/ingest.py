"""Ingest the frozen 20-call baseline from Sarvam Analytics into redacted JSONL."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from sarvam_voice_agents.analytics import SarvamAnalyticsClient, redact_attempt
from sarvam_voice_agents.config import Settings


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SELECTION = Path(__file__).with_name("baseline_selection.json")
DEFAULT_OUTPUT = ROOT / "artifacts" / "baseline" / "calls.jsonl"
DEFAULT_METADATA = ROOT / "artifacts" / "baseline" / "corpus.json"


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _read_selection(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list) or not value:
        raise ValueError("baseline selection must be a non-empty JSON array")
    attempts = [item.get("attempt_id") for item in value]
    if len(attempts) != len(set(attempts)):
        raise ValueError("baseline selection contains duplicate attempt_id")
    return value


def build_corpus(
    *,
    selection: list[dict[str, Any]],
    attempts: list[dict[str, Any]],
    transcript_fetcher: Any,
) -> list[dict[str, Any]]:
    by_attempt = {item.get("attempt_id"): item for item in attempts}
    records: list[dict[str, Any]] = []
    for selected in selection:
        attempt_id = selected["attempt_id"]
        attempt = by_attempt.get(attempt_id)
        if attempt is None:
            raise ValueError(f"selected attempt was not returned by Sarvam: {attempt_id}")
        interaction_id = attempt.get("interaction_id")
        transcript = transcript_fetcher(interaction_id)
        messages = transcript.get("messages", [])
        record = {
            "schema_version": "baseline-call.v1",
            "run_id": selected["run_id"],
            "scenario_id": selected["scenario_id"],
            "corpus_role": selected["corpus_role"],
            "benchmark_member": bool(selected["benchmark_member"]),
            "primary_eligible": bool(selected["primary_eligible"]),
            "expected_disposition": selected["expected_disposition"],
            "source": {
                "platform": "sarvam_indus",
                "app_version": 12,
                "attempt_id": attempt_id,
                "interaction_id": interaction_id,
            },
            "attempt": redact_attempt(attempt),
            "messages": messages,
        }
        record["record_sha256"] = canonical_hash(record)
        records.append(record)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--start", default="2026-08-17T13:30:00Z")
    parser.add_argument("--end", default="2026-08-17T15:30:00Z")
    args = parser.parse_args()

    settings = Settings.from_environment(env_file=args.env_file)
    client = SarvamAnalyticsClient(
        api_key=settings.api_key,
        org_id=settings.org_id,
        workspace_id=settings.workspace_id,
        app_id=settings.app_id,
    )
    selection = _read_selection(args.selection)
    attempts = client.list_attempts(start_datetime=args.start, end_datetime=args.end)
    records = build_corpus(
        selection=selection,
        attempts=attempts,
        transcript_fetcher=client.get_transcript,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    metadata = {
        "schema_version": "baseline-corpus.v1",
        "call_count": len(records),
        "benchmark_count": sum(item["benchmark_member"] for item in records),
        "exploratory_count": sum(not item["benchmark_member"] for item in records),
        "source_app_version": 12,
        "selection_sha256": canonical_hash(selection),
        "records_sha256": canonical_hash([item["record_sha256"] for item in records]),
        "pii_policy": "direct contact identifiers and recording URLs removed",
    }
    args.metadata.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
