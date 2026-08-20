"""Build the Loopline demo gallery from preserved evaluation artifacts.

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

TOOL_CATALOGUE = [
    {"name": "check_payment_status", "kind": "read", "description": "Read the ledger's payment status and outstanding amount. Never invents completion."},
    {"name": "record_promise_to_pay", "kind": "write", "description": "Write a confirmed future payment date. Requires DD-MM-YYYY."},
    {"name": "schedule_callback", "kind": "write", "description": "Write a callback preference. Requires an absolute date and a narrow IST window."},
    {"name": "record_disposition", "kind": "write", "description": "Close the episode with exactly one of the twelve allowed terminal outcomes."},
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
        "scenario_id": "EMI-DYN-003",
        "tier": "stateful_text",
        "kind": "comparison",
        "baseline": "v12-dynamic-full",
        "baseline_label": "As deployed",
        "candidate": "v15-firm-today-full",
        "candidate_label": "After improvement",
        "candidate_rescored": True,
        "headline": "Both agents say they are noting 20 August. Only one wrote it down.",
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
        "scenario_id": "EMI-DYN-005",
        "tier": "stateful_text",
        "kind": "single",
        "experiment": "v15-firm-today-full",
        "rescored": True,
        "headline": "schedule_callback writes a date and a narrow window; the assertion normalises the format.",
        "why": "Shows what a write tool actually has to get right — and that the checker compares meaning, not string equality.",
    },
    {
        "id": "punjabi-switch",
        "title": "Switches to Punjabi and still lands the tool call.",
        "scenario_id": "EMI-DYN-013",
        "tier": "stateful_text",
        "kind": "single",
        "experiment": "v15-firm-today-full",
        "rescored": True,
        "headline": "Language adaptation without losing the date, the amount, or the write.",
        "why": "The reference benchmark for this work is English-only. Indian voice agents fail at exactly this seam, so it is measured here rather than assumed.",
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
        "id": "drift-caught",
        "title": "The deployed prompt had drifted. The framework judged it.",
        "scenario_id": "EMI-DYN-030",
        "tier": "stateful_text",
        "kind": "comparison",
        "baseline": "v16-indus-drift-full-20260820T200723Z",
        "baseline_label": "Drifted draft",
        "candidate": "v15-firm-today-full",
        "candidate_label": "Approved agent",
        "candidate_rescored": True,
        "headline": "An in-platform copilot silently rewrote the approved agent. It scored 22/30 against the real one's 30/30.",
        "why": "The drifted draft was captured, hashed, registered as V16 and run through the same evaluator rather than argued about. On this scenario both refuse the OTP correctly — but the evaluator only recognises one phrasing as safe, which is now filed as an evaluator repair.",
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

    payload = {
        "schema_version": "loopline-gallery.v1",
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
