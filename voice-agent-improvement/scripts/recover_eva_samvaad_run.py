"""Recover a completed Samvaad call that EVA archived as a transport failure.

This is an evidence-preserving normalization step, not a simulated rerun.  It
copies the raw archived attempt, verifies the matching read-only Indus analytics
record, projects authoritative output variables into the scenario state, and
marks an Indus `AGENT_ENDS` call as `assistant_completed`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "artifacts" / "eva_live"
RECORD_ID = "EMI-LIVE-001"
IST = ZoneInfo("Asia/Kolkata")

sys.path.insert(0, str(ROOT))

from sarvam_voice_agents.analytics import SarvamAnalyticsClient  # noqa: E402


def _hash_dict(value: dict) -> str:
    serialized = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(serialized.encode()).hexdigest()


def _load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected JSON object: {path}")
    return value


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def _find_attempt(client: SarvamAnalyticsClient, result: dict, interaction_id: str) -> dict:
    started = datetime.fromisoformat(str(result["started_at"]))
    ended = datetime.fromisoformat(str(result["ended_at"]))
    if started.tzinfo is None:
        started = started.replace(tzinfo=IST)
    if ended.tzinfo is None:
        ended = ended.replace(tzinfo=IST)
    attempts = client.list_attempts(
        start_datetime=(started - timedelta(minutes=10)).isoformat(),
        end_datetime=(ended + timedelta(minutes=10)).isoformat(),
        limit=100,
    )
    matches = [attempt for attempt in attempts if attempt.get("interaction_id") == interaction_id]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one Indus attempt for {interaction_id}; found {len(matches)}")
    return matches[0]


def recover(run_id: str) -> Path:
    run_dir = OUTPUT_ROOT / run_id
    records_dir = run_dir / "records"
    destination = records_dir / RECORD_ID
    if destination.exists():
        raise RuntimeError(f"Refusing to overwrite existing normalized record: {destination}")
    archived = sorted(records_dir.glob(f"{RECORD_ID}_failed_attempt_*"))
    if not archived:
        raise RuntimeError(f"No archived attempt found under {records_dir}")
    normalized_archives = [
        path
        for path in archived
        if (path / "result.json").exists()
        and _load_json(path / "result.json").get("conversation_ended_reason") == "assistant_completed"
    ]
    source = normalized_archives[-1] if normalized_archives else archived[-1]
    shutil.copytree(source, destination)

    result = _load_json(destination / "result.json")
    runtime = _load_json(destination / "samvaad_runtime.json")
    interaction_id = str(runtime.get("interaction_id") or "")
    if not interaction_id:
        raise RuntimeError("Archived run has no Samvaad interaction_id")

    import os

    client = SarvamAnalyticsClient(
        api_key=os.environ["SARVAM_VOICE_AGENTS_API_KEY"],
        org_id=os.environ["SARVAM_ORG_ID"],
        workspace_id=os.environ["SARVAM_WORKSPACE_ID"],
        app_id=os.environ["SARVAM_APP_ID"],
    )
    attempt = _find_attempt(client, result, interaction_id)
    if attempt.get("connectivity_status") != "connected" or attempt.get("ended_by") != "AGENT_ENDS":
        raise RuntimeError(
            "Refusing terminal normalization without connected + AGENT_ENDS evidence: "
            f"connectivity={attempt.get('connectivity_status')}, ended_by={attempt.get('ended_by')}"
        )

    redacted_attempt = {
        key: value
        for key, value in attempt.items()
        if key not in {"audio_url", "user_contact", "user_contact_hashed", "user_identifier"}
    }
    redacted_attempt["recording_available"] = bool(attempt.get("audio_url"))
    _write_json(destination / "samvaad_attempt.json", redacted_attempt)

    initial = _load_json(destination / "initial_scenario_db.json")
    final = _load_json(destination / "final_scenario_db.json")
    initial_variables = initial.get("agent_variables", {})
    attempt_variables = attempt.get("agent_variables", {})
    changed = {
        key: value
        for key, value in attempt_variables.items()
        if key not in initial_variables or value != initial_variables.get(key)
    }
    runtime["variables"] = changed
    runtime["analytics_source"] = "Sarvam Analytics attempts API"
    _write_json(destination / "samvaad_runtime.json", runtime)

    customer = final.setdefault("customer", {})
    if changed.get("disposition"):
        customer["outcome"] = changed["disposition"]
    if changed.get("promisedToPayDate") not in {None, "", "NA"}:
        customer["promise_to_pay_date"] = changed["promisedToPayDate"]
    if changed.get("callbackDateTime") not in {None, "", "NA"}:
        customer["callback_at"] = changed["callbackDateTime"]
    _write_json(destination / "final_scenario_db.json", final)

    result["completed"] = True
    result["conversation_ended_reason"] = "assistant_completed"
    result["error"] = None
    result["error_details"] = None
    result["initial_scenario_db_hash"] = _hash_dict(initial)
    result["final_scenario_db_hash"] = _hash_dict(final)
    result["output_dir"] = str(destination)
    for key in (
        "audio_assistant_path",
        "audio_mixed_path",
        "audio_user_path",
        "audit_log_path",
        "conversation_log_path",
        "pipecat_logs_path",
        "transcript_path",
        "user_simulator_logs_path",
    ):
        stored = result.get(key)
        if stored:
            result[key] = str(destination / Path(stored).name)
    _write_json(destination / "result.json", result)

    events_path = destination / "user_simulator_events.jsonl"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if events and events[-1].get("type") == "connection_state":
        details = events[-1].setdefault("data", {}).setdefault("details", {})
        details["original_reason"] = details.get("reason")
        details["reason"] = "assistant_completed"
        events_path.write_text(
            "".join(json.dumps(event, ensure_ascii=False, default=str) + "\n" for event in events),
            encoding="utf-8",
        )

    # Preserve the pre-recovery score for auditability, but keep EVA from
    # reusing a cached transport-failure score against the normalized record.
    prior_metrics = destination / "metrics.json"
    if prior_metrics.exists():
        prior_metrics.replace(destination / "metrics.pre_recovery.json")

    _write_json(
        destination / "recovery_manifest.json",
        {
            "source_archive": str(source),
            "normalized_record": str(destination),
            "interaction_id": interaction_id,
            "evidence": {
                "connectivity_status": attempt.get("connectivity_status"),
                "ended_by": attempt.get("ended_by"),
                "failure_reason": attempt.get("failure_reason"),
                "disposition": changed.get("disposition"),
            },
            "normalization": {
                "conversation_ended_reason": "assistant_completed",
                "scenario_outcome": customer.get("outcome"),
                "provider_rerun": False,
            },
        },
    )
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env", override=False)
    destination = recover(args.run_id)
    print(json.dumps({"status": "recovered", "record_dir": str(destination)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
