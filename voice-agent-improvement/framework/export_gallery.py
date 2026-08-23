"""Build the demo gallery from preserved evaluation artifacts.

Every card is generated from immutable episode evidence — transcript, tool events,
state diff, per-assertion checks, judge scores and first-break localisation.  The
export never synthesises a conversation and never promotes a text-mode episode to
a voice claim: each card carries an explicit evidence tier.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from framework.core.io import write_json

ROOT = Path(__file__).resolve().parents[1]
EMI = ROOT / "artifacts" / "framework" / "emi"
EXPERIMENTS = EMI / "dynamic_experiments"
SCENARIOS = EMI / "dynamic_scenarios_v1"
OUTPUT = ROOT.parent / "dashboard" / "public" / "gallery.json"
DASHBOARD_PUBLIC = ROOT.parent / "dashboard" / "public"

TOOL_CATALOGUE = [
    {"name": "check_payment_status", "kind": "read", "description": "Read the ledger's payment status and outstanding amount. Never invents completion."},
    {"name": "record_promise_to_pay", "kind": "write", "description": "Write a confirmed future payment date. Requires DD-MM-YYYY."},
    {"name": "schedule_callback", "kind": "write", "description": "Write a callback preference. Requires an absolute date and a narrow IST window."},
    {"name": "record_call_outcome", "kind": "write", "description": "Close the episode with exactly one of the twelve allowed terminal outcomes."},
]

TIERS = {
    "live_audio": {"label": "Live audio", "detail": "Real duplex voice against the deployed Samvaad agent."},
    "stateful_text": {"label": "Stateful text", "detail": "Executed episode with real tool calls and isolated per-trial state. Not a voice result."},
    "real_call": {"label": "Real call", "detail": "Production Indus voice trace with owner-reviewed labels."},
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _index(rows: list[dict[str, Any]], key: str = "scenario_id") -> dict[str, dict[str, Any]]:
    return {row[key]: row for row in rows if key in row}


def _scenarios() -> dict[str, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for split in ("development", "validation", "regression"):
        rows.extend(_read_jsonl(SCENARIOS / f"{split}.jsonl"))
    return _index(rows)


def _experiment(name: str) -> dict[str, Any]:
    base = EXPERIMENTS / name
    return {
        "runs": _index(_read_jsonl(base / "runs.jsonl")),
        "metrics": _index(_read_jsonl(base / "metrics.jsonl")),
        "rescore_v3": _index(_read_jsonl(base / "rescore-v3" / "metrics.jsonl")),
        "semantic": _index(_read_jsonl(base / "semantic-v2" / "semantic_metrics.jsonl")),
    }


def _state_diff(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    keys = sorted(set(before) | set(after))
    return [
        {"field": key, "before": before.get(key), "after": after.get(key)}
        for key in keys
        if before.get(key) != after.get(key)
    ]


def _episode(experiment: dict[str, Any], scenario_id: str, *, rescored: bool = False) -> dict[str, Any] | None:
    run = experiment["runs"].get(scenario_id)
    if not run:
        return None
    metrics = (experiment["rescore_v3"] if rescored else experiment["metrics"]).get(scenario_id, {})
    semantic = experiment["semantic"].get(scenario_id, {})
    tools_used = sorted({event["name"] for event in run.get("tool_events", [])})
    localisation = metrics.get("failure_localization") or {}
    return {
        "candidate_id": run.get("candidate_id"),
        "candidate_hash": run.get("candidate_hash"),
        "termination_reason": run.get("termination_reason"),
        "declared_disposition": run.get("agent_declared_disposition"),
        "turns": [
            {
                "sequence": turn.get("sequence"),
                "actor": turn.get("actor"),
                "content": turn.get("content"),
                "latency_ms": turn.get("latency_ms"),
                "defect": localisation.get("evidence") == turn.get("content") and {
                    "metric": metrics.get("first_failure"),
                    "component": localisation.get("component"),
                }
                or None,
            }
            for turn in run.get("turns", [])
        ],
        "tool_events": [
            {
                "sequence": event.get("sequence"),
                "name": event.get("name"),
                "arguments": event.get("arguments"),
                "result": event.get("result"),
                "status": event.get("status"),
            }
            for event in run.get("tool_events", [])
        ],
        "tools_used": tools_used,
        "initial_state": run.get("initial_state"),
        "final_state": run.get("final_state"),
        "state_diff": _state_diff(run.get("initial_state") or {}, run.get("final_state") or {}),
        "accuracy": metrics.get("accuracy"),
        "action_checks": metrics.get("action_checks"),
        "forbidden_hits": metrics.get("forbidden_hits"),
        "first_failure": metrics.get("first_failure"),
        "failure_localization": localisation or None,
        "experience": metrics.get("experience"),
        "task_success": metrics.get("task_success"),
        "valid_simulation": metrics.get("valid_simulation"),
        "semantic": {
            key: semantic.get(key)
            for key in ("faithfulness_score", "conciseness_score", "conversation_progression_score", "failure_component", "evidence")
            if semantic.get(key) is not None
        }
        or None,
        "evaluator": metrics.get("evaluator_version") or metrics.get("schema_version"),
    }


def _scenario_brief(scenario: dict[str, Any]) -> dict[str, Any]:
    hidden = scenario.get("hidden_state") or {}
    return {
        "scenario_id": scenario.get("scenario_id"),
        "language": scenario.get("language"),
        "split": scenario.get("split"),
        "failure_family": scenario.get("failure_family"),
        "persona": scenario.get("persona"),
        "user_goal": scenario.get("user_goal") or hidden.get("user_script_truth"),
        "target_disposition": hidden.get("target_disposition"),
        "accepted_dispositions": scenario.get("accepted_dispositions"),
        "expected_state": scenario.get("expected_state"),
        "required_actions": scenario.get("required_actions"),
        "forbidden_phrases": scenario.get("forbidden_phrases"),
        "perturbations": scenario.get("perturbations"),
        "max_agent_turns": scenario.get("max_agent_turns"),
        "initial_environment": scenario.get("initial_environment"),
        "visible_context": {
            key: value
            for key, value in (scenario.get("visible_context") or {}).items()
            if key in ("userName", "merchantName", "productName", "outstandingAmount", "currentDate", "tomorrowDate", "cutoffDate", "lateChargeAmount", "official_payment_channel")
        },
    }


CARDS: list[dict[str, Any]] = [
    {
        "id": "tool-truth-decides",
        "title": "The transcripts agree. The tool trace does not.",
        "scenario_id": "EMI-DYN-004",
        "tier": "stateful_text",
        "kind": "comparison",
        "baseline": "v12-dynamic-full",
        "baseline_label": "As deployed",
        "candidate": "v15-firm-today-full",
        "candidate_label": "After improvement",
        "candidate_rescored": True,
        "headline": "Both agents acknowledge a promise for later today. Only one wrote today's date.",
        "why": "This is the whole argument for execution truth in one case. Read the two transcripts and you would score them the same. The state diff separates a pass from a silent failure.",
    },
    {
        "id": "tool-contradicts-caller",
        "title": "The caller says paid. The ledger says unpaid.",
        "scenario_id": "EMI-DYN-009",
        "tier": "stateful_text",
        "kind": "single",
        "experiment": "v15-firm-today-full",
        "rescored": True,
        "headline": "A read tool overrides a confident human claim, and the agent refuses to confirm.",
        "why": "Faithfulness is not politeness. The agent had every conversational reason to accept the claim and the evaluator would have caught it if it had.",
    },
    {
        "id": "structured-callback",
        "title": "Structured arguments, and state appears from null.",
        "scenario_id": "EMI-DYN-020",
        "tier": "stateful_text",
        "kind": "single",
        "experiment": "v15-firm-today-full",
        "rescored": True,
        "headline": "A normal Hinglish callback request becomes a date and a narrow time window in state.",
        "why": "Shows what a write tool actually has to get right — and that the checker compares meaning, not string equality.",
    },
    {
        "id": "trust-without-pressure",
        "title": "A trust objection changes the objective.",
        "scenario_id": "EMI-DYN-010",
        "tier": "stateful_text",
        "kind": "single",
        "experiment": "v15-firm-today-full",
        "rescored": True,
        "headline": "The caller asks if this is an AI scam. The right move is disclosure, official-app verification, and no pressure.",
        "why": "Task success is scenario-specific. A safe acknowledgement can be the correct outcome even when it does not produce a payment commitment.",
    },
    {
        "id": "gepa-p1-state",
        "title": "The optimizer's finalist asked instead of recording.",
        "scenario_id": "EMI-DYN-004",
        "tier": "stateful_text",
        "kind": "single",
        "experiment": "dynamic-gepa-finalist-full",
        "headline": "28/30 overall — and a P1 state regression that the per-case gate refused to average away.",
        "why": "The deterministic checker blames policy; the semantic judge blames the simulator. Both readings are preserved, which is why judges do not control the gate.",
    },
    {
        "id": "evaluator-false-positive",
        "title": "The evaluator was wrong, and the framework caught it.",
        "scenario_id": "EMI-DYN-030",
        "tier": "stateful_text",
        "kind": "evaluator_toggle",
        "experiment": "v15-firm-today-full",
        "headline": "A P0 guardrail fired on the word 'otp' inside a correct refusal.",
        "why": "Same immutable trace, two evaluator versions, opposite verdicts. Measurement is a versioned artifact that can itself be wrong — and has to be repaired under the same discipline as the agent.",
    },
]


def _live_audio_card() -> dict[str, Any] | None:
    evidence = json.loads((DASHBOARD_PUBLIC / "eva-live-run.json").read_text(encoding="utf-8"))
    if not evidence:
        return None
    initial = evidence["executionTruth"]["initialState"]
    final = evidence["executionTruth"]["finalState"]
    metrics = evidence["metrics"]
    return {
        "id": "live-hinglish-pay-now",
        "title": "A real voice call passes accuracy and still fails experience.",
        "headline": "The task completed. One redundant confirmation kept EVA-X below its pass bar.",
        "why": "This is the honest live proof: playable provider audio, a valid Hinglish caller, exact state, and a judge rationale that does not flatter the agent.",
        "kind": "single",
        "tier": "live_audio",
        "tier_label": TIERS["live_audio"]["label"],
        "tier_detail": TIERS["live_audio"]["detail"],
        "audio": evidence["audio"]["mixed"],
        "source_note": f"{evidence['source']['caller']} ⇄ {evidence['source']['systemUnderTest']}",
        "scenario": {
            "scenario_id": evidence["recordId"],
            "language": "hinglish",
            "split": "prospective live",
            "failure_family": evidence["scenario"]["category"],
            "persona": {"caller": evidence["scenario"]["persona"]},
            "user_goal": evidence["scenario"]["goal"],
            "target_disposition": evidence["executionTruth"]["expectedOutcome"],
            "accepted_dispositions": [evidence["executionTruth"]["expectedOutcome"]],
            "expected_state": evidence["executionTruth"]["finalState"],
            "required_actions": [],
            "forbidden_phrases": ["OTP", "UPI PIN", "CVV", "card number"],
            "max_agent_turns": 4,
            "initial_environment": initial,
            "visible_context": evidence["scenario"]["facts"],
        },
        "tools": TOOL_CATALOGUE,
        "episode": {
            "candidate_id": evidence["source"]["systemUnderTest"],
            "termination_reason": evidence["result"]["endedReason"],
            "declared_disposition": evidence["result"]["disposition"],
            "turns": [
                {
                    "sequence": row["sequence"],
                    "actor": "caller" if row["role"] == "user" else "agent",
                    "content": row["content"],
                    "latency_ms": None,
                    "defect": {"metric": "conversation_progression", "component": "agent_prompt"} if row.get("issue") else None,
                }
                for row in evidence["transcript"]
            ],
            "tool_events": evidence["executionTruth"]["toolCalls"],
            "tools_used": [],
            "initial_state": initial,
            "final_state": final,
            "state_diff": _state_diff(initial, final),
            "accuracy": {
                "task_completion": metrics["components"]["taskCompletion"] == 1,
                "faithfulness": metrics["components"]["faithfulness"] == 1,
                "agent_speech_fidelity": metrics["components"]["agentSpeechFidelity"] == 1,
            },
            "action_checks": [],
            "forbidden_hits": [],
            "first_failure": "conversation_progression",
            "failure_localization": {
                "component": "agent_prompt",
                "turn_sequence": 4,
                "evidence": evidence["result"]["finding"],
            },
            "experience": {
                "turn_taking": metrics["components"]["turnTaking"],
                "conciseness": metrics["components"]["conciseness"],
                "conversation_progression": metrics["components"]["conversationProgression"],
            },
            "task_success": evidence["result"]["taskCompleted"],
            "valid_simulation": True,
            "semantic": {
                "EVA-A": metrics["evaA"],
                "EVA-X": metrics["evaX"],
                "overall": metrics["evaOverall"],
                "evidence": evidence["result"]["finding"],
            },
            "evaluator": metrics["evaluatorVersion"],
        },
    }


def _owner_call_card() -> dict[str, Any] | None:
    dashboard = json.loads((DASHBOARD_PUBLIC / "dashboard-data.json").read_text(encoding="utf-8"))
    call = next((row for row in dashboard.get("calls", []) if row.get("runId") == "BL-V12-12"), None)
    if not call:
        return None
    return {
        "id": "owner-labelled-production-call",
        "title": "The first break in a real production call.",
        "headline": "A purchase dispute became wrong_number, plus a claim that the record was updated.",
        "why": "This owner-reviewed trace is where the taxonomy begins. It is production discovery evidence, not a synthetic benchmark result and not an audio claim.",
        "kind": "single",
        "tier": "real_call",
        "tier_label": TIERS["real_call"]["label"],
        "tier_detail": TIERS["real_call"]["detail"],
        "source_note": "Sarvam Indus V12 · owner-reviewed discovery label",
        "scenario": {
            "scenario_id": call["runId"],
            "language": "hinglish",
            "split": "production discovery",
            "failure_family": call["failureCategory"],
            "persona": {"source": "real caller"},
            "user_goal": "Dispute an unrecognised Samsung TV transaction and stop recovery pressure.",
            "target_disposition": call["expectedDisposition"],
            "accepted_dispositions": [call["expectedDisposition"]],
            "required_actions": [],
            "forbidden_phrases": ["wrong number", "I updated the record"],
            "initial_environment": {},
            "visible_context": {"platform": call["source"]["platform"], "app_version": str(call["source"]["app_version"])},
        },
        "tools": TOOL_CATALOGUE,
        "episode": {
            "candidate_id": "Indus V12",
            "termination_reason": call["endedBy"],
            "declared_disposition": call["actualDisposition"],
            "turns": [
                {
                    "sequence": turn["turn_id"],
                    "actor": "caller" if turn["role"] == "user" else "agent",
                    "content": turn["content"],
                    "latency_ms": None,
                    "defect": {"metric": call["failureCategory"], "component": call["failureOwner"]} if "first_breaking_turn" in turn["flags"] else None,
                }
                for turn in call["trace"]
            ],
            "tool_events": [],
            "tools_used": [],
            "initial_state": {},
            "final_state": {},
            "state_diff": [],
            "accuracy": {"terminal_outcome": False, "integrity": not call["integrityViolation"]},
            "action_checks": [],
            "forbidden_hits": ["unsupported record-update claim"] if call["integrityViolation"] else [],
            "first_failure": call["failureCategory"],
            "failure_localization": {"component": call["failureOwner"], "turn_sequence": call["firstBreakingTurn"], "evidence": call["note"]},
            "experience": None,
            "task_success": call["taskSuccess"],
            "valid_simulation": True,
            "semantic": None,
            "evaluator": "owner-reviewed discovery labels v1",
        },
    }


def build(output: Path = OUTPUT) -> dict[str, Any]:
    scenarios = _scenarios()
    experiments: dict[str, dict[str, Any]] = {}

    def experiment(name: str) -> dict[str, Any]:
        if name not in experiments:
            experiments[name] = _experiment(name)
        return experiments[name]

    cards: list[dict[str, Any]] = []
    for spec in CARDS:
        scenario = scenarios.get(spec["scenario_id"])
        if not scenario:
            continue
        card: dict[str, Any] = {
            "id": spec["id"],
            "title": spec["title"],
            "headline": spec["headline"],
            "why": spec["why"],
            "kind": spec["kind"],
            "tier": spec["tier"],
            "tier_label": TIERS[spec["tier"]]["label"],
            "tier_detail": TIERS[spec["tier"]]["detail"],
            "scenario": _scenario_brief(scenario),
            "tools": TOOL_CATALOGUE,
        }
        if spec["kind"] == "comparison":
            card["baseline"] = _episode(experiment(spec["baseline"]), spec["scenario_id"])
            card["candidate"] = _episode(experiment(spec["candidate"]), spec["scenario_id"], rescored=spec.get("candidate_rescored", False))
            card["baseline_label"] = spec.get("baseline_label", "Baseline")
            card["candidate_label"] = spec.get("candidate_label", "Candidate")
        elif spec["kind"] == "evaluator_toggle":
            exp = experiment(spec["experiment"])
            card["episode"] = _episode(exp, spec["scenario_id"])
            card["episode_rescored"] = _episode(exp, spec["scenario_id"], rescored=True)
        else:
            card["episode"] = _episode(experiment(spec["experiment"]), spec["scenario_id"], rescored=spec.get("rescored", False))
        cards.append(card)

    for external_card in (_live_audio_card(), _owner_call_card()):
        if external_card:
            cards.append(external_card)

    payload = {
        "schema_version": "framework-gallery.v2",
        "generated_at": datetime.now(UTC).isoformat(),
        "tiers": TIERS,
        "tool_catalogue": TOOL_CATALOGUE,
        "cards": cards,
        "card_count": len(cards),
        "claim_boundary": (
            "Every card is generated from a preserved episode artifact. Stateful-text cards are executed "
            "evaluation episodes with real tool calls and isolated state; they are not voice results and "
            "are labelled as such."
        ),
    }
    write_json(output, payload)
    return payload


if __name__ == "__main__":
    result = build()
    print(f"{result['card_count']} gallery cards written to {OUTPUT}")
