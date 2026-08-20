"""Fetch every recent Indus attempt into a redacted operational trace feed."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from improvement.evaluate import ROOT
from improvement.ingest import _read_selection
from sarvam_voice_agents.analytics import SarvamAnalyticsClient, redact_attempt
from sarvam_voice_agents.config import Settings


DEFAULT_OUTPUT = ROOT / "artifacts" / "monitoring" / "calls.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.hours < 1:
        parser.error("--hours must be positive")

    settings = Settings.from_environment(env_file=args.env_file)
    client = SarvamAnalyticsClient(
        api_key=settings.api_key,
        org_id=settings.org_id,
        workspace_id=settings.workspace_id,
        app_id=settings.app_id,
    )
    end = dt.datetime.now(dt.timezone.utc)
    start = end - dt.timedelta(hours=args.hours)
    attempts = client.list_attempts(
        start_datetime=start.isoformat().replace("+00:00", "Z"),
        end_datetime=end.isoformat().replace("+00:00", "Z"),
    )
    existing_records: dict[str, dict[str, Any]] = {}
    if args.output.exists():
        for line in args.output.read_text(encoding="utf-8").splitlines():
            if line.strip():
                item = json.loads(line)
                existing_records[item["source"]["attempt_id"]] = item
    selected = {item["attempt_id"]: item for item in _read_selection(Path(__file__).with_name("baseline_selection.json"))}
    records: list[dict[str, Any]] = []
    for attempt in attempts:
        attempt_id = str(attempt.get("attempt_id", ""))
        interaction_id = str(attempt.get("interaction_id", ""))
        cached = existing_records.get(attempt_id)
        cache_is_current = bool(
            cached
            and cached.get("attempt", {}).get("end_datetime") == attempt.get("end_datetime")
            and cached.get("attempt", {}).get("num_messages") == attempt.get("num_messages")
        )
        transcript = (
            {"messages": cached.get("messages", [])}
            if cache_is_current
            else client.get_transcript(interaction_id) if interaction_id else {"messages": []}
        )
        selection = selected.get(attempt_id)
        records.append({
            "schema_version": "operational-call.v1",
            "run_id": selection["run_id"] if selection else f"UNTRACKED-{attempt_id[:8]}",
            "evaluation_status": "frozen_baseline" if selection else "not_evaluated",
            "selection": selection,
            "source": {"platform": "sarvam_indus", "attempt_id": attempt_id, "interaction_id": interaction_id},
            "attempt": redact_attempt(attempt),
            "messages": transcript.get("messages", []),
        })

    records.sort(key=lambda item: str(item["attempt"].get("start_datetime", "")), reverse=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({
        "recent_attempts": len(records),
        "evaluated": sum(item["evaluation_status"] == "frozen_baseline" for item in records),
        "not_evaluated": sum(item["evaluation_status"] == "not_evaluated" for item in records),
        "window_hours": args.hours,
        "transcripts_fetched": sum(
            not (
                existing_records.get(str(item.get("attempt_id", "")))
                and existing_records[str(item.get("attempt_id", ""))].get("attempt", {}).get("end_datetime") == item.get("end_datetime")
                and existing_records[str(item.get("attempt_id", ""))].get("attempt", {}).get("num_messages") == item.get("num_messages")
            )
            for item in attempts
        ),
        "pii_policy": "contact identifiers and recording URLs removed",
    }, indent=2))


if __name__ == "__main__":
    main()
