"""Deterministic diagnostics for the paired Indus acoustic stress matrix."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from statistics import mean
from typing import Any

from framework.core.io import read_jsonl, write_json, write_jsonl


def _intent_recognized(transcripts: list[str]) -> bool:
    text = " ".join(transcripts).lower()
    now = any(token in text for token in ("अभी", "abhi", "now"))
    payment = any(token in text for token in ("पेमेंट", "payment", "pay"))
    action = any(token in text for token in ("करता", "करूंगा", "करूँगा", "karta", "karunga"))
    return now and payment and action


def _brand_exact(transcripts: list[str]) -> bool:
    text = " ".join(transcripts).lower()
    normalized = re.sub(r"\s+", " ", text)
    return any(token in normalized for token in ("easycredit", "easy credit", "ईज़ी क्रेडिट", "ईजी क्रेडिट"))


def _redundant_confirmation(agent_text: str) -> bool:
    text = agent_text.lower()
    return "?" in text and any(token in text for token in ("अभी", "abhi", "now")) and any(token in text for token in ("पेमेंट", "payment", "pay"))


def evaluate(run_path: Path, output_dir: Path) -> dict[str, Any]:
    rows = []
    for run in read_jsonl(run_path):
        transcripts = run.get("provenance", {}).get("observed_user_transcripts", [])
        agent_turns = [turn for turn in run.get("turns", []) if turn.get("actor") == "agent"]
        final_agent_text = agent_turns[-1]["content"] if agent_turns else ""
        latency = agent_turns[-1].get("latency_ms") if agent_turns else None
        rows.append(
            {
                "schema_version": "voice-stress-metrics.v1",
                "scenario_id": run["scenario_id"],
                "interaction_id": run.get("interaction_id"),
                "conditions": run.get("provenance", {}).get("audio_perturbations", []),
                "stt_pay_now_intent_recognized": _intent_recognized(transcripts),
                "brand_entity_exact": _brand_exact(transcripts),
                "agent_response_captured": bool(agent_turns),
                "redundant_confirmation": _redundant_confirmation(final_agent_text),
                "last_agent_latency_ms": latency,
                "observed_user_transcripts": transcripts,
                "last_agent_evidence": final_agent_text,
                "claim_boundary": "Synthetic-speaker acoustic diagnostic. Entity misses may arise from local TTS pronunciation, transport, or Indus STT and are not component-attributed here.",
            }
        )
    latencies = [item["last_agent_latency_ms"] for item in rows if item["last_agent_latency_ms"] is not None]
    latency_comparable = all(
        run.get("provenance", {}).get("latency_semantics") == "end_of_user_audio_to_completed_agent_audio"
        for run in read_jsonl(run_path)
    )
    summary = {
        "schema_version": "voice-stress-summary.v1",
        "records": len(rows),
        "stt_intent_recognition_rate": round(sum(item["stt_pay_now_intent_recognized"] for item in rows) / len(rows), 4) if rows else 0,
        "brand_entity_exact_rate": round(sum(item["brand_entity_exact"] for item in rows) / len(rows), 4) if rows else 0,
        "redundant_confirmation_rate": round(sum(item["redundant_confirmation"] for item in rows) / len(rows), 4) if rows else 0,
        "average_last_agent_latency_ms": round(mean(latencies), 1) if latencies and latency_comparable else None,
        "latency_definition": (
            "End-of-user-audio to completed agent audio."
            if latency_comparable
            else "Legacy run included user streaming time; latency intentionally suppressed and must not be compared."
        ),
        "reliability": {
            "intent_pass_at_1": round(sum(item["stt_pay_now_intent_recognized"] for item in rows) / len(rows), 4) if rows else 0,
            "intent_pass_all_conditions": bool(rows) and all(item["stt_pay_now_intent_recognized"] for item in rows),
            "policy_pass_all_conditions": bool(rows) and not any(item["redundant_confirmation"] for item in rows),
        },
        "claim_boundary": "One paired synthetic voice and six deterministic channel conditions. This diagnoses transfer behavior; it is not a human population estimate or candidate voice A/B.",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "voice_metrics.jsonl", rows)
    write_json(output_dir / "voice_summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_path", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.run_path, args.output_dir), indent=2))


if __name__ == "__main__":
    main()
