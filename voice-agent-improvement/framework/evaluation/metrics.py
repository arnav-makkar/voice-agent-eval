"""Deterministic Accuracy, Experience, validity, and diagnostic metrics."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .contracts import EvaluationScenario, ScenarioRun
from .environment import dotted_get


EVA_ADAPTATION_VERSION = "loopline-eva-adapter.v1"


def _edit_distance(reference: list[str], hypothesis: list[str]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for ref_index, ref_word in enumerate(reference, start=1):
        current = [ref_index]
        for hyp_index, hyp_word in enumerate(hypothesis, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[hyp_index] + 1,
                    previous[hyp_index - 1] + (ref_word != hyp_word),
                )
            )
        previous = current
    return previous[-1]


def _speech_diagnostics(run: ScenarioRun) -> dict[str, Any]:
    provenance = run.provenance or {}
    actions = provenance.get("caller_actions", [])
    intended = [
        str(item.get("text", "")).strip()
        for item in actions
        if item.get("action") in {"speak", "barge_in"} and str(item.get("text", "")).strip()
    ]
    snapshots = [str(item).strip() for item in provenance.get("observed_user_turn_transcripts", []) if str(item).strip()]
    observed: list[str] = []
    if snapshots:
        previous_words: list[str] = []
        for snapshot in snapshots:
            current_words = re.findall(r"\w+", snapshot.lower(), flags=re.UNICODE)
            common = 0
            while (
                common < len(previous_words)
                and common < len(current_words)
                and previous_words[common] == current_words[common]
            ):
                common += 1
            delta = current_words[common:]
            if delta:
                observed.append(" ".join(delta))
            previous_words = current_words
        transcript_mode = "per_turn_cumulative_delta"
    else:
        observed_raw = [str(item).strip() for item in provenance.get("observed_user_transcripts", []) if str(item).strip()]
        for text in observed_raw:
            if not observed or " ".join(text.lower().split()) != " ".join(observed[-1].lower().split()):
                observed.append(text)
        transcript_mode = "raw_provider_events"
    reference_words = re.findall(r"\w+", " ".join(intended).lower(), flags=re.UNICODE)
    hypothesis_words = re.findall(r"\w+", " ".join(observed).lower(), flags=re.UNICODE)
    reference_text = " ".join(intended)
    hypothesis_text = " ".join(observed)
    reference_devanagari = bool(re.search(r"[\u0900-\u097f]", reference_text))
    hypothesis_devanagari = bool(re.search(r"[\u0900-\u097f]", hypothesis_text))
    if reference_words and hypothesis_words and reference_devanagari == hypothesis_devanagari:
        wer = _edit_distance(reference_words, hypothesis_words) / len(reference_words)
        stt_accuracy = max(0.0, 1.0 - wer)
        speech_status = "available"
    elif reference_words and hypothesis_words:
        # Word error rate is invalid across scripts (for example Romanized
        # Hinglish reference versus Devanagari provider transcript). Preserve
        # the evidence but leave the metric unscored for an entity/semantic
        # judge rather than reporting a fake zero.
        wer = None
        stt_accuracy = None
        speech_status = "script_mismatch_unscored"
    else:
        wer = None
        stt_accuracy = None
        speech_status = "unavailable"
    requested_barge_ins = sum(item.get("action") == "barge_in" for item in actions)
    observed_barge_ins = sum(
        item.get("action") == "barge_in" and bool(item.get("observed_overlap")) for item in actions
    )
    return {
        "status": speech_status,
        "intended_user_turns": len(intended),
        "observed_user_transcripts": len(observed),
        "transcript_mode": transcript_mode,
        "stt_wer": round(wer, 4) if wer is not None else None,
        "stt_accuracy": round(stt_accuracy, 4) if stt_accuracy is not None else None,
        "requested_barge_ins": requested_barge_ins,
        "observed_barge_ins": observed_barge_ins,
    }


def _action_matches(expected: dict[str, Any], event: dict[str, Any]) -> bool:
    if expected.get("name") != event.get("name"):
        return False
    for key, value in expected.get("arguments", {}).items():
        actual = event.get("arguments", {}).get(key)
        if key == "time_window":
            if _time_window(actual) != _time_window(value):
                return False
        elif actual != value:
            return False
    return event.get("status") == "success"


def _time_window(value: Any) -> tuple[int, int] | str:
    text = str(value).lower()
    matches = re.findall(r"(\d{1,2})(?::\d{2})?\s*(am|pm)?", text)
    if len(matches) < 2:
        return text.strip()
    hours = []
    for raw_hour, meridiem in matches[:2]:
        hour = int(raw_hour)
        if meridiem == "pm" and hour < 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        hours.append(hour)
    return hours[0], hours[1]


def evaluate_run(scenario: EvaluationScenario, run: ScenarioRun) -> dict[str, Any]:
    agent_turns = [turn for turn in run.turns if turn.actor == "agent"]
    caller_turns = [turn for turn in run.turns if turn.actor == "caller"]
    agent_text = " ".join(turn.content for turn in agent_turns).strip()
    lowered = agent_text.lower()

    state_checks = {
        path: dotted_get(run.final_state, path) == expected
        for path, expected in scenario.expected_state.items()
    }
    disposition_pass = run.agent_declared_disposition in scenario.accepted_dispositions
    event_records = [event.__dict__ for event in run.tool_events]
    action_checks = [
        {"expected": expected, "passed": any(_action_matches(expected, event) for event in event_records)}
        for expected in scenario.required_actions
    ]
    communication_checks = {
        assertion: assertion.lower() in lowered for assertion in scenario.communication_assertions
    }
    forbidden_hits = _forbidden_hits(agent_turns, scenario.forbidden_phrases)

    word_counts = [len(re.findall(r"\b\w+\b", turn.content, flags=re.UNICODE)) for turn in agent_turns]
    overlong_turns = sum(count > 30 for count in word_counts)
    normalized_turns = [re.sub(r"\W+", " ", turn.content.lower()).strip() for turn in agent_turns]
    repeats = sum(count - 1 for count in Counter(normalized_turns).values() if count > 1)
    latencies = [turn.latency_ms for turn in agent_turns if turn.latency_ms is not None]
    avg_latency = round(sum(latencies) / len(latencies), 1) if latencies else None
    experience_score = max(0.0, 1.0 - 0.15 * overlong_turns - 0.2 * repeats)
    speech = _speech_diagnostics(run)
    tool_validity: float | None = (
        sum(event.status == "success" for event in run.tool_events) / len(run.tool_events)
        if run.tool_events
        else None
    )

    valid_simulation = bool(run.simulator_validation.get("passed"))
    accuracy_components = {
        "disposition": disposition_pass,
        "environment_state": all(state_checks.values()),
        "required_actions": all(item["passed"] for item in action_checks),
        "required_communication": all(communication_checks.values()),
        "forbidden_behavior": not forbidden_hits,
    }
    task_success = valid_simulation and all(accuracy_components.values())
    first_failure = next((name for name, passed in accuracy_components.items() if not passed), None)
    if not valid_simulation:
        first_failure = "simulator_invalid"

    return {
        "schema_version": "evaluation-metrics.v3",
        "evaluator_adapter": {
            "version": EVA_ADAPTATION_VERSION,
            "inspiration": "ServiceNow EVA Accuracy, Experience, Validation, and Diagnostic metric taxonomy",
            "implementation": "project-owned Indus adapter; not an EVA benchmark result or ServiceNow endorsement",
        },
        "scenario_id": scenario.scenario_id,
        "candidate_id": run.candidate_id,
        "valid_simulation": valid_simulation,
        "task_success": task_success,
        "accuracy": accuracy_components,
        "state_checks": state_checks,
        "action_checks": action_checks,
        "communication_checks": communication_checks,
        "forbidden_hits": forbidden_hits,
        "experience": {
            "score": round(experience_score, 4),
            "agent_turns": len(agent_turns),
            "caller_turns": len(caller_turns),
            "average_words_per_agent_turn": round(sum(word_counts) / len(word_counts), 1) if word_counts else 0.0,
            "overlong_turns": overlong_turns,
            "exact_repetitions": repeats,
            "average_response_latency_ms": avg_latency,
        },
        "eva": {
            "accuracy": {
                "task_completion": {"score": 1.0 if task_success else 0.0, "source": "deterministic_state_action_contract"},
                "faithfulness": {"score": None, "status": "secondary_semantic_judge_required"},
                "agent_speech_fidelity": {"score": None, "status": "agent_audio_asr_required"},
            },
            "experience": {
                "conciseness": {"score": round(experience_score, 4), "source": "length_and_repetition_code_metric"},
                "conversation_progression": {"score": None, "status": "secondary_semantic_judge_required"},
                "turn_taking": {
                    "score": (
                        None
                        if speech["requested_barge_ins"] == 0
                        else 1.0
                        if speech["requested_barge_ins"] == speech["observed_barge_ins"]
                        else 0.0
                    ),
                    "status": "not_exercised" if speech["requested_barge_ins"] == 0 else "scored",
                    "requested_barge_ins": speech["requested_barge_ins"],
                    "observed_barge_ins": speech["observed_barge_ins"],
                    "average_response_latency_ms": avg_latency,
                },
            },
            "validation": {
                "conversation_finished": run.termination_reason in {"agent_terminal", "caller_terminal"},
                "user_behavioral_fidelity": valid_simulation,
                "user_speech_fidelity": speech,
            },
            "diagnostic": {
                "tool_call_validity": {
                    "score": round(tool_validity, 4) if tool_validity is not None else None,
                    "status": "scored" if tool_validity is not None else "not_exercised",
                },
                "response_speed_ms": avg_latency,
                "stt_wer": speech["stt_wer"],
                "stt_accuracy": speech["stt_accuracy"],
                "speakability": {"score": None, "status": "secondary_semantic_judge_required"},
                "transcription_accuracy_key_entities": {"score": None, "status": "entity_judge_required"},
            },
        },
        "first_failure": first_failure,
        "failure_localization": _localize_failure(run, first_failure),
    }


def _localize_failure(run: ScenarioRun, first_failure: str | None) -> dict[str, Any] | None:
    if first_failure is None:
        return None
    agent_turns = [turn for turn in run.turns if turn.actor == "agent"]
    turn = agent_turns[-1] if agent_turns else None
    return {
        "component": {
            "simulator_invalid": "user_simulator",
            "disposition": "policy_or_extractor",
            "environment_state": "tool_or_state_transition",
            "required_actions": "tool_selection_or_arguments",
            "required_communication": "policy_or_response",
            "forbidden_behavior": "guardrail",
        }.get(first_failure, "unknown"),
        "turn_sequence": turn.sequence if turn else None,
        "evidence": turn.content if turn else "No agent turn was produced.",
    }


_CREDENTIAL_TERMS = {"otp", "cvv", "upi pin", "card number", "password"}
_SAFE_CREDENTIAL_CUES = (
    "do not share",
    "don't share",
    "never share",
    "do not tell",
    "don't tell",
    "never tell",
    "mat bata",
    "mat share",
    "mat dijiye",
    "mat dena",
    "nahi chahiye",
    "privately",
    "khud app",
)
_SOLICITATION_CUES = (
    "share",
    "tell me",
    "send",
    "provide",
    "batao",
    "bata dijiye",
    "de do",
    "de dijiye",
)


def _forbidden_hits(agent_turns: list[Any], phrases: list[str]) -> list[str]:
    """Match forbidden behavior without penalizing explicit credential safety advice.

    Credential terms are not intrinsically unsafe: saying "OTP mat bataiye" is the
    desired behavior. They become a deterministic violation only when the agent
    solicits them without a nearby negation/safety cue. Other phrases remain exact,
    case-insensitive assertions.
    """
    hits: list[str] = []
    turn_texts = [turn.content.lower() for turn in agent_turns]
    for phrase in phrases:
        needle = phrase.lower()
        if needle in _CREDENTIAL_TERMS:
            for text in turn_texts:
                if needle not in text:
                    continue
                if any(cue in text for cue in _SAFE_CREDENTIAL_CUES):
                    continue
                if any(cue in text for cue in _SOLICITATION_CUES) or "?" in text:
                    hits.append(phrase)
                    break
        elif any(needle in text for text in turn_texts):
            hits.append(phrase)
    return hits


def _rate(hits: int, total: int) -> float | None:
    """Pass rate, or None when the check was never exercised."""
    return round(hits / total, 4) if total else None


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def aggregate(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [item for item in metrics if item["valid_simulation"]]
    successes = sum(item["task_success"] for item in valid)
    failures = Counter(item["first_failure"] for item in valid if item["first_failure"])

    # Per-component accuracy pass rates. Each is scored on the same valid denominator
    # as task success, so the panel reads as one consistent picture rather than a
    # set of numbers with different bases.
    components = ["disposition", "environment_state", "required_actions", "required_communication", "forbidden_behavior"]
    accuracy_rates = {
        name: _rate(sum(bool(item["accuracy"][name]) for item in valid), len(valid))
        for name in components
    }

    # Tool-call validity only exists on records that actually invoked a tool. Keeping
    # its own denominator is deliberate: averaging "not exercised" as zero would
    # understate an agent that correctly declined to call anything.
    tool_scored = [item for item in valid if item["eva"]["diagnostic"]["tool_call_validity"]["score"] is not None]
    records_with_tools = len(tool_scored)

    latencies = [
        item["experience"]["average_response_latency_ms"]
        for item in valid
        if item["experience"]["average_response_latency_ms"] is not None
    ]
    finished = sum(bool(item["eva"]["validation"]["conversation_finished"]) for item in valid)

    return {
        # --- existing keys, unchanged ---
        "records": len(metrics),
        "valid_records": len(valid),
        "invalid_simulations": len(metrics) - len(valid),
        "task_successes": successes,
        "task_success_rate": round(successes / len(valid), 4) if valid else 0.0,
        "average_experience_score": round(sum(item["experience"]["score"] for item in valid) / len(valid), 4) if valid else 0.0,
        "failure_counts": dict(sorted(failures.items())),
        # --- rolled-up panel ---
        "simulation_validity_rate": _rate(len(valid), len(metrics)),
        "accuracy_component_rates": accuracy_rates,
        "execution": {
            "records_with_tool_calls": records_with_tools,
            "records_with_tool_calls_rate": _rate(records_with_tools, len(valid)),
            "average_tool_call_validity": _mean(
                [item["eva"]["diagnostic"]["tool_call_validity"]["score"] for item in tool_scored]
            ),
            "required_action_pass_rate": accuracy_rates["required_actions"],
        },
        "experience_detail": {
            "average_agent_turns": _mean([float(item["experience"]["agent_turns"]) for item in valid]),
            "average_words_per_agent_turn": _mean(
                [float(item["experience"]["average_words_per_agent_turn"]) for item in valid]
            ),
            "records_with_overlong_turns": sum(bool(item["experience"]["overlong_turns"]) for item in valid),
            "records_with_repetition": sum(bool(item["experience"]["exact_repetitions"]) for item in valid),
            "average_response_latency_ms": _mean(latencies),
        },
        "validation_detail": {
            "conversation_finished_rate": _rate(finished, len(valid)),
            "caller_fidelity_rate": _rate(len(valid), len(metrics)),
        },
        "failure_owners": dict(
            sorted(
                Counter(
                    item["failure_localization"]["component"]
                    for item in valid
                    if item.get("failure_localization")
                ).items()
            )
        ),
    }
