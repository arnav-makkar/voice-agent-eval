"""EVA-inspired semantic Accuracy/Experience metrics with cited failure turns."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from framework.adapters.gemini import GeminiJsonClient, load_env_file
from framework.core.io import read_jsonl, write_json, write_jsonl


ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ROOT / "artifacts" / "framework" / "emi" / "dynamic_scenarios_v1"

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "judgments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "scenario_id": {"type": "string"},
                    "faithfulness_score": {"type": "integer", "minimum": 0, "maximum": 4},
                    "conciseness_score": {"type": "integer", "minimum": 0, "maximum": 4},
                    "conversation_progression_score": {"type": "integer", "minimum": 0, "maximum": 4},
                    "user_behavior_fidelity": {"type": "boolean"},
                    "factual_error": {"type": "boolean"},
                    "integrity_violation": {"type": "boolean"},
                    "forbidden_behavior_violation": {"type": "boolean"},
                    "first_failure_turn": {"type": "integer", "minimum": 0},
                    "failure_component": {"type": "string", "enum": ["none", "simulator", "agent_policy", "tool_selection", "tool_execution", "knowledge", "extractor", "voice_or_transcript", "unknown"]},
                    "evidence": {"type": "string"},
                },
                "required": ["scenario_id", "faithfulness_score", "conciseness_score", "conversation_progression_score", "user_behavior_fidelity", "factual_error", "integrity_violation", "forbidden_behavior_violation", "first_failure_turn", "failure_component", "evidence"],
            },
        }
    },
    "required": ["judgments"],
}


def _scenario_index() -> dict[str, dict[str, Any]]:
    result = {}
    for split in ("development", "validation", "regression", "fresh_final"):
        path = SCENARIOS / f"{split}.jsonl"
        if path.exists():
            result.update({item["scenario_id"]: item for item in read_jsonl(path)})
    return result


def judge(run_path: Path, output_dir: Path, *, model: str = "gemini-pro-latest", batch_size: int = 6) -> dict[str, Any]:
    load_env_file(ROOT / ".env")
    scenarios = _scenario_index()
    runs = read_jsonl(run_path)
    client = GeminiJsonClient(model=model, cache_dir=ROOT / "artifacts" / "framework" / "cache")
    judgments: list[dict[str, Any]] = []
    metadata = []
    for offset in range(0, len(runs), batch_size):
        batch = runs[offset : offset + batch_size]
        payload = []
        for run in batch:
            scenario = scenarios[run["scenario_id"]]
            payload.append(
                {
                    "scenario_id": run["scenario_id"],
                    "user_goal": scenario["user_goal"],
                    "hidden_reference": scenario["hidden_state"],
                    "expected_user_steps": scenario["user_steps"],
                    "exact_visible_facts": scenario["visible_context"],
                    "accepted_dispositions": scenario["accepted_dispositions"],
                    "forbidden_phrases": scenario["forbidden_phrases"],
                    "transcript": run["turns"],
                    "tool_events": run["tool_events"],
                    "final_state": run["final_state"],
                    "simulator_validation": run["simulator_validation"],
                }
            )
        response = client.complete_json(
            system=(
                "You are the secondary semantic judge for a voice-agent evaluation framework. The deterministic final-state and action graders remain primary. "
                "Score faithfulness, conciseness, and conversation progression from 0 to 4. Faithfulness means every claim is supported by supplied facts or tool state. "
                "Progression means each agent turn advances the task without repeating a resolved question or pressuring after a terminal response. "
                "A check/try is not a commitment and a commitment is not completed payment. Credential safety advice such as 'OTP kisi ko mat dijiye' is correct guardrail behavior, not a forbidden-behavior violation. "
                "Judge user behavior fidelity only by comparing caller turns with expected_user_steps and the user goal; a wrong-party persona following its scripted denial is valid. "
                "Locate the first failing turn; use 0 and component=none when no failure exists. Cite a short exact phrase as evidence. Judge the user simulator separately; do not blame the agent for invalid simulator execution."
            ),
            user=json.dumps({"evaluator_version": "dynamic-eva-metrics-v2", "episodes": payload}, ensure_ascii=False),
            response_schema=SCHEMA,
            temperature=0,
            thinking_level="high",
            cache_namespace="dynamic_semantic/dynamic-eva-metrics-v2",
        )
        expected = [item["scenario_id"] for item in payload]
        returned = [item.get("scenario_id") for item in response.data["judgments"]]
        if expected != returned:
            raise ValueError(f"judge order mismatch: expected {expected}, got {returned}")
        judgments.extend(response.data["judgments"])
        metadata.append(response.metadata)
    valid = [item for item in judgments if item["user_behavior_fidelity"]]
    summary = {
        "schema_version": "dynamic-semantic-summary.v2",
        "evaluator_version": "dynamic-eva-metrics-v2",
        "model": model,
        "records": len(judgments),
        "valid_records": len(valid),
        "average_faithfulness": round(sum(item["faithfulness_score"] for item in valid) / len(valid), 3) if valid else 0,
        "average_conciseness": round(sum(item["conciseness_score"] for item in valid) / len(valid), 3) if valid else 0,
        "average_progression": round(sum(item["conversation_progression_score"] for item in valid) / len(valid), 3) if valid else 0,
        "factual_errors": sum(item["factual_error"] for item in valid),
        "integrity_violations": sum(item["integrity_violation"] for item in valid),
        "forbidden_behavior_violations": sum(item["forbidden_behavior_violation"] for item in valid),
        "judge_calls": metadata,
        "claim_boundary": "Secondary LLM-judge diagnostics; deterministic state/action checks are primary and human calibration is required for final claims.",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "semantic_metrics.jsonl", judgments)
    write_json(output_dir / "semantic_summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_path", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--model", default="gemini-pro-latest")
    args = parser.parse_args()
    print(json.dumps(judge(args.run_path, args.output_dir, model=args.model), indent=2))


if __name__ == "__main__":
    main()
