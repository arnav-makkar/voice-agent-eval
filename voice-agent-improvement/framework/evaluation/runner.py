"""Run isolated multi-turn scenarios and persist replayable traces."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from framework.core.io import write_json, write_jsonl

from .candidates import CandidateAgent
from .contracts import ConversationTurn, EvaluationScenario, ScenarioRun, ToolEvent
from .environment import EMIEnvironment, ToolExecutionError
from .metrics import aggregate, evaluate_run


def run_scenario(candidate: CandidateAgent, scenario: EvaluationScenario, candidate_hash: str) -> ScenarioRun:
    started = datetime.now(UTC)
    environment = EMIEnvironment.from_initial(scenario.initial_environment)
    initial_state = environment.snapshot()
    turns: list[ConversationTurn] = []
    tool_events: list[ToolEvent] = []
    history: list[dict[str, str]] = []
    tool_history: list[dict[str, Any]] = []
    final_disposition = "call_disconnected"
    termination_reason = "script_exhausted"
    model_metadata: list[dict[str, Any]] = []

    for step_index, user_step in enumerate(scenario.user_steps, start=1):
        turns.append(ConversationTurn(len(turns) + 1, "caller", user_step.text))
        history.append({"role": "caller", "content": user_step.text})
        terminal = False
        seen_tool_calls: set[str] = set()
        for tool_round in range(3):
            response = candidate.respond(
                visible_context=scenario.visible_context,
                history=history,
                tool_history=tool_history,
            )
            spoken = str(response["spoken_response"]).strip()
            if spoken:
                turns.append(ConversationTurn(len(turns) + 1, "agent", spoken, float(response.get("latency_ms", 0))))
                history.append({"role": "agent", "content": spoken})
            model_metadata.append(response.get("provenance", {}))
            raw_calls = response.get("tool_calls", [])
            for raw_call in raw_calls:
                sequence = len(tool_events) + 1
                name = str(raw_call.get("name", ""))
                arguments = dict(raw_call.get("arguments", {}))
                fingerprint = json.dumps({"name": name, "arguments": arguments}, sort_keys=True)
                tool_started = time.perf_counter()
                if fingerprint in seen_tool_calls:
                    result = {"error": "duplicate tool call in one agent turn"}
                    status = "error"
                else:
                    seen_tool_calls.add(fingerprint)
                    try:
                        result = environment.execute(name, arguments)
                        status = "success"
                    except ToolExecutionError as exc:
                        result = {"error": str(exc)}
                        status = "error"
                event = ToolEvent(sequence, name, arguments, result, status, round((time.perf_counter() - tool_started) * 1000, 2))
                tool_events.append(event)
                tool_history.append(event.__dict__)
            disposition = str(response.get("disposition", "continue"))
            if disposition != "continue":
                final_disposition = disposition
                if not any(event.name == "record_call_outcome" and event.status == "success" for event in tool_events):
                    try:
                        environment.execute("record_call_outcome", {"disposition": disposition})
                    except ToolExecutionError:
                        pass
            if response.get("should_end_call") or disposition != "continue":
                termination_reason = "agent_terminal"
                terminal = True
                break
            if not raw_calls:
                break
            # The next model step receives the deterministic tool result before
            # the scripted caller speaks again, matching real agent execution.
            if tool_round == 2:
                termination_reason = "tool_loop_limit"
        if terminal:
            break
        if step_index >= scenario.max_agent_turns:
            termination_reason = "max_turns"
            break

    consumed_caller_turns = sum(turn.actor == "caller" for turn in turns)
    expected_caller_turns = min(len(scenario.user_steps), scenario.max_agent_turns)
    simulator_validation = {
        "passed": consumed_caller_turns > 0 and consumed_caller_turns <= expected_caller_turns,
        "consumed_steps": consumed_caller_turns,
        "available_steps": len(scenario.user_steps),
        "termination_was_explicit": termination_reason == "agent_terminal",
    }
    ended = datetime.now(UTC)
    return ScenarioRun(
        schema_version="scenario-run.v1",
        run_id=f"RUN-{started.strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}",
        scenario_id=scenario.scenario_id,
        candidate_id=candidate.candidate_id,
        candidate_hash=candidate_hash,
        adapter=candidate.adapter_name,
        started_at=started.isoformat(),
        ended_at=ended.isoformat(),
        termination_reason=termination_reason,
        interaction_id=None,
        turns=turns,
        tool_events=tool_events,
        initial_state=initial_state,
        final_state=environment.snapshot(),
        agent_declared_disposition=final_disposition,
        simulator_validation=simulator_validation,
        provenance={"model_calls": model_metadata},
    )


def run_suite(
    candidate: CandidateAgent,
    prompt: str,
    scenarios: list[EvaluationScenario],
    output_dir: Path,
) -> dict[str, Any]:
    candidate_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    evaluator_paths = [
        Path(__file__),
        Path(__file__).with_name("contracts.py"),
        Path(__file__).with_name("environment.py"),
        Path(__file__).with_name("metrics.py"),
        Path(__file__).with_name("release.py"),
    ]
    evaluator_hash = hashlib.sha256(b"".join(path.read_bytes() for path in evaluator_paths)).hexdigest()
    scenario_set_hash = hashlib.sha256(
        "\n".join(sorted(scenario.to_record()["content_hash"] for scenario in scenarios)).encode("utf-8")
    ).hexdigest()
    output_dir.mkdir(parents=True, exist_ok=True)
    runs: list[ScenarioRun] = []
    metrics: list[dict[str, Any]] = []
    for scenario in scenarios:
        run = run_scenario(candidate, scenario, candidate_hash)
        runs.append(run)
        metrics.append(evaluate_run(scenario, run))
        # Checkpoint after every complete episode so a failed provider request
        # still leaves auditable partial evidence instead of an empty directory.
        write_jsonl(output_dir / "runs.partial.jsonl", [item.to_record() for item in runs])
        write_jsonl(output_dir / "metrics.partial.jsonl", metrics)
    run_records = [run.to_record() for run in runs]
    summary = {
        "schema_version": "evaluation-suite-summary.v1",
        "candidate_id": candidate.candidate_id,
        "candidate_hash": candidate_hash,
        "evaluator_bundle_sha256": evaluator_hash,
        "scenario_set_sha256": scenario_set_hash,
        "adapter": candidate.adapter_name,
        "scenario_count": len(scenarios),
        "splits": sorted({scenario.split for scenario in scenarios}),
        "source_groups": sorted({scenario.source_group for scenario in scenarios}),
        "aggregate": aggregate(metrics),
        "run_ids": [run.run_id for run in runs],
        "claim_boundary": "Text-mode stateful evaluation. Audio/STT/TTS and production payment lift require matched Indus voice evidence.",
    }
    write_jsonl(output_dir / "runs.jsonl", run_records)
    write_jsonl(output_dir / "metrics.jsonl", metrics)
    write_json(output_dir / "summary.json", summary)
    (output_dir / "runs.partial.jsonl").unlink(missing_ok=True)
    (output_dir / "metrics.partial.jsonl").unlink(missing_ok=True)
    return summary


def load_scenarios(path: Path) -> list[EvaluationScenario]:
    return [
        EvaluationScenario.from_record(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
