"""Deterministically audit a completed EVA/Samvaad voice run.

This is a post-flight safety layer, not another LLM score. It catches evidence
gaps that aggregate EVA metrics can obscure: required tools that never ran,
terminal success claims without a state write, stale expected dates, and a
non-Hinglish Indic-script switch in the deployed agent transcript.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any


NON_HINGLISH_INDIC = re.compile(r"[\u0980-\u09ff\u0a00-\u0a7f\u0a80-\u0aff\u0b00-\u0bff\u0c00-\u0dff]")
TERMINAL_SUCCESS_CLAIM = re.compile(
    r"(schedule(?:d)? (?:kar diya|कर दिया)|callback schedule|record (?:kar leta|कर लेता)|recorded|"
    r"darj kar diya|note kar leta)",
    re.IGNORECASE,
)


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        day, month, year = value.split("-")
        return date(int(year), int(month), int(day))
    except (TypeError, ValueError):
        return None


def audit_record(record_dir: Path) -> dict[str, Any]:
    initial = _json(record_dir / "initial_scenario_db.json")
    final = _json(record_dir / "final_scenario_db.json")
    state = _json(record_dir / "loopline_tool_state.json") if (record_dir / "loopline_tool_state.json").exists() else {}
    transcript = _jsonl(record_dir / "transcript.jsonl")
    required = initial.get("evaluation", {}).get("required_actions", [])
    events = state.get("events", [])
    tool_names = [event.get("tool_name") for event in events]
    findings: list[dict[str, Any]] = []

    missing = [action["name"] for action in required if action.get("name") not in tool_names]
    if missing:
        findings.append({"rule": "required_tool_missing", "severity": "P0", "evidence": missing})

    current = date.fromisoformat(initial.get("_current_date", "2026-08-19"))
    stale_dates = []
    for action in required:
        action_date = _parse_date(action.get("arguments", {}).get("date"))
        if action_date and action_date < current:
            stale_dates.append(action.get("arguments", {}).get("date"))
    if stale_dates:
        findings.append({"rule": "stale_expected_date", "severity": "P0", "evidence": stale_dates})

    assistant_text = [
        str(turn.get("content") or turn.get("text") or "")
        for turn in transcript
        if (turn.get("role") or turn.get("speaker") or turn.get("type")) == "assistant"
    ]
    script_switches = [text for text in assistant_text if NON_HINGLISH_INDIC.search(text)]
    if script_switches:
        findings.append(
            {
                "rule": "non_hinglish_indic_script",
                "severity": "P1",
                "evidence": script_switches[:2],
            }
        )

    unsupported_claims = [text for text in assistant_text if TERMINAL_SUCCESS_CLAIM.search(text)]
    if unsupported_claims and not events:
        findings.append(
            {
                "rule": "terminal_claim_without_tool_evidence",
                "severity": "P0",
                "evidence": unsupported_claims[:2],
            }
        )

    state_changed = initial.get("customer") != final.get("customer")
    return {
        "record_id": record_dir.name,
        "completed": not record_dir.name.endswith("_failed_attempt_1"),
        "tool_events": tool_names,
        "state_changed": state_changed,
        "findings": findings,
        "passes_postflight": not findings,
    }


def audit_run(run_dir: Path) -> dict[str, Any]:
    records = [audit_record(path) for path in sorted((run_dir / "records").iterdir()) if path.is_dir()]
    completed = [row for row in records if row["completed"]]
    return {
        "schema_version": "loopline-voice-postflight.v1",
        "run_id": run_dir.name,
        "records": records,
        "attempted": len(records),
        "completed": len(completed),
        "postflight_passes": sum(row["passes_postflight"] for row in completed),
        "decision": "HOLD",
        "decision_reasons": sorted({finding["rule"] for row in records for finding in row["findings"]}),
        "claim_boundary": (
            "This deterministic post-flight supplements EVA; it does not alter EVA-A or EVA-X. A candidate cannot "
            "advance when either EVA task completion or this post-flight fails."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit_run(args.run_dir.resolve())
    output = args.output or args.run_dir / "loopline_postflight.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": report["decision"], "reasons": report["decision_reasons"], "output": str(output)}, indent=2))


if __name__ == "__main__":
    main()
