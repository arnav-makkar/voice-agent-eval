"""Export the latest valid EVA/Samvaad run into the presentation dashboard.

The dashboard consumes this compact, secret-free projection. The source EVA
artifacts remain immutable and are always referenced by run_id/record_id.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVA_DIR = ROOT / "artifacts" / "eva_live"
DEFAULT_DASHBOARD = ROOT.parent / "dashboard" / "public"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def latest_valid_run(eva_dir: Path) -> Path:
    valid: list[Path] = []
    for run_dir in eva_dir.iterdir():
        status_path = run_dir / "attempt_status.json"
        if not status_path.exists():
            continue
        if read_json(status_path).get("classification") == "valid_live_bot_to_bot_evaluation":
            valid.append(run_dir)
    if not valid:
        raise RuntimeError(f"No valid EVA live run found in {eva_dir}")
    return sorted(valid, key=lambda path: path.name)[-1]


def metric_score(metrics: dict, name: str) -> float | None:
    raw = (metrics.get("metrics") or {}).get(name)
    if not isinstance(raw, dict):
        return None
    score = raw.get("normalized_score", raw.get("score"))
    return float(score) if isinstance(score, (int, float)) else None


def aggregate_score(metrics: dict, name: str) -> float | None:
    score = (metrics.get("aggregate_metrics") or {}).get(name)
    return float(score) if isinstance(score, (int, float)) else None


def public_customer(customer: dict) -> dict:
    """Project historical state without the obsolete synthetic surname."""
    projected = dict(customer)
    if str(projected.get("name", "")).startswith("Arnav"):
        projected["name"] = "Arnav"
    return projected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--dashboard-public", type=Path, default=DEFAULT_DASHBOARD)
    args = parser.parse_args()

    run_dir = args.run_dir or latest_valid_run(DEFAULT_EVA_DIR)
    status = read_json(run_dir / "attempt_status.json")
    record_id = status["record_id"]
    record_dir = run_dir / "records" / record_id

    result = read_json(record_dir / "result.json")
    initial_state = read_json(record_dir / "initial_scenario_db.json")
    final_state = read_json(record_dir / "final_scenario_db.json")
    attempt = read_json(record_dir / "samvaad_attempt.json")
    metrics = read_json(record_dir / "metrics.json")
    latencies = read_json(record_dir / "response_latencies.json")
    dataset = read_json(ROOT / "research" / "upstream" / "eva" / "data" / "emi_dataset.json")
    scenario = next(item for item in dataset if item["id"] == record_id)

    transcript = []
    for index, line in enumerate((record_dir / "transcript.jsonl").read_text(encoding="utf-8").splitlines()):
        event = json.loads(line)
        transcript.append(
            {
                "sequence": index + 1,
                "timestamp": event.get("timestamp"),
                "role": event.get("role") or event.get("type"),
                "content": event.get("content", ""),
                "issue": (
                    "Redundant confirmation after an explicit pay-now commitment."
                    if index == 3
                    else None
                ),
            }
        )

    goal = scenario["user_goal"]
    output = {
        "schemaVersion": "framework-submission-evidence.v2",
        "runId": status["run_id"],
        "recordId": record_id,
        "source": {
            "runDirectory": str(run_dir),
            "recordDirectory": str(record_dir),
            "evaluator": "EVA 2.1.0 + project-owned Samvaad adapter",
            "systemUnderTest": "Sarvam Samvaad V12 — Shubh",
            "caller": "ElevenLabs realtime agent — Arnav",
        },
        "scenario": {
            "category": scenario["category"],
            "goal": goal["high_level_user_goal"],
            "persona": scenario["user_config"]["user_persona"],
            "mustHave": goal["decision_tree"]["must_have_criteria"],
            "niceToHave": goal["decision_tree"].get("nice_to_have_criteria", []),
            "behavior": goal["decision_tree"]["negotiation_behavior"],
            "resolution": goal["decision_tree"]["resolution_condition"],
            "failure": goal["decision_tree"]["failure_condition"],
            "facts": goal["information_required"],
        },
        "providerEvidence": {
            "sarvamConnectivity": attempt["connectivity_status"],
            "sarvamEndedBy": attempt["ended_by"],
            "sarvamFailureReason": attempt["failure_reason"],
            "sarvamDurationSeconds": attempt["duration_in_seconds"],
            "sarvamAverageAgentResponseSeconds": attempt["average_agent_response_time_in_seconds"],
            "bridgeMeanResponseSeconds": latencies.get("mean"),
            "elevenLabsDurationSeconds": status["provider_evidence"]["elevenlabs_duration_seconds"],
            "transport": "live bidirectional audio over WebSocket",
        },
        "metrics": {
            "conversationValidEnd": metric_score(metrics, "conversation_valid_end"),
            "userBehavioralFidelity": metric_score(metrics, "user_behavioral_fidelity"),
            "userSpeechFidelity": metric_score(metrics, "user_speech_fidelity"),
            "evaA": aggregate_score(metrics, "EVA-A_mean"),
            "evaX": aggregate_score(metrics, "EVA-X_mean"),
            "evaOverall": aggregate_score(metrics, "EVA-overall_mean"),
            "evaAPass": aggregate_score(metrics, "EVA-A_pass") == 1.0,
            "evaXPass": aggregate_score(metrics, "EVA-X_pass") == 1.0,
            "evaOverallPass": aggregate_score(metrics, "EVA-overall_pass") == 1.0,
            "compositeStatus": "computed_v7",
            "evaluatorVersion": "evaluation-metrics.v3/framework-eva-adapter.v1/samvaad-duplex.v7",
            "components": {
                "taskCompletion": metric_score(metrics, "task_completion"),
                "faithfulness": metric_score(metrics, "faithfulness"),
                "agentSpeechFidelity": metric_score(metrics, "agent_speech_fidelity"),
                "turnTaking": metric_score(metrics, "turn_taking"),
                "conciseness": metric_score(metrics, "conciseness"),
                "conversationProgression": metric_score(metrics, "conversation_progression"),
            },
        },
        "executionTruth": {
            "initialState": public_customer(initial_state["customer"]),
            "finalState": public_customer(final_state["customer"]),
            "expectedOutcome": "payment_ready",
            "actualOutcome": final_state["customer"].get("outcome"),
            "finalStateMatchesExpected": status["execution_truth"]["final_state_matches_expected"],
            "toolCalls": result.get("tools_called", []),
            "toolCallCount": result.get("num_tool_calls", 0),
        },
        "result": {
            "completed": result["completed"],
            "endedReason": result["conversation_ended_reason"],
            "taskCompleted": status["product_finding"]["task_completed"],
            "experiencePerfect": status["product_finding"]["experience_perfect"],
            "finding": status["product_finding"]["description"],
            "disposition": attempt["agent_variables"]["disposition"],
        },
        "transcript": transcript,
        "audio": {
            "mixed": "/evidence/eva-live/audio_mixed.wav",
            "caller": "/evidence/eva-live/elevenlabs_audio_recording.mp3",
        },
    }

    target_dir = args.dashboard_public / "evidence" / "eva-live"
    target_dir.mkdir(parents=True, exist_ok=True)
    (args.dashboard_public / "eva-live-run.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    shutil.copy2(record_dir / "audio_mixed.wav", target_dir / "audio_mixed.wav")
    shutil.copy2(record_dir / "elevenlabs_audio_recording.mp3", target_dir / "elevenlabs_audio_recording.mp3")
    print(args.dashboard_public / "eva-live-run.json")


if __name__ == "__main__":
    main()
