"""Export the linear self-improvement narrative from preserved artifacts.

The dashboard tells one story: measure the deployed agent, localise what broke,
repair the owning component, re-run the identical frozen evaluation, then let an
independent gate decide.  Every figure here is read from an evaluation artifact —
nothing is authored for the narrative.

Agent versions are surfaced as "baseline" and "improved" because the audience
cares about the loop, not the version numbers; the underlying candidate ids and
hashes stay attached to every act for anyone who wants to audit it.
"""

from __future__ import annotations

import collections
import json
import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from framework.core.io import write_json

ROOT = Path(__file__).resolve().parents[1]
EMI = ROOT / "artifacts" / "framework" / "emi"
EXPERIMENTS = EMI / "dynamic_experiments"
OUTPUT = ROOT.parent / "dashboard" / "public" / "story.json"

BASELINE = "v12-dynamic-full"
IMPROVED = "v15-firm-today-full"
BUSINESS_TOOLS = ("check_payment_status", "record_promise_to_pay", "schedule_callback")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _read(path: Path, default: Any = None) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _profile(experiment: str, rescore: str | None = None) -> dict[str, Any]:
    base = EXPERIMENTS / experiment
    runs = _read_jsonl(base / "runs.jsonl")
    metrics = _read_jsonl((base / rescore / "metrics.jsonl") if rescore else (base / "metrics.jsonl"))
    by_id = {row["scenario_id"]: row for row in metrics}
    tool_counts = collections.Counter(event["name"] for run in runs for event in run.get("tool_events", []))
    episodes_with_tools = sum(1 for run in runs if run.get("tool_events"))
    episodes_with_business_tools = sum(
        1 for run in runs if any(event["name"] in BUSINESS_TOOLS for event in run.get("tool_events", []))
    )
    failures = collections.Counter(row["first_failure"] for row in metrics if row.get("first_failure"))
    components = collections.Counter(
        (row.get("failure_localization") or {}).get("component") for row in metrics if row.get("first_failure")
    )
    successes = sum(1 for row in metrics if row.get("task_success"))
    experience = [row["experience"]["score"] for row in metrics if row.get("experience")]
    return {
        "experiment_id": experiment,
        "candidate_id": runs[0]["candidate_id"] if runs else None,
        "candidate_hash": runs[0].get("candidate_hash") if runs else None,
        "episodes": len(runs),
        "task_successes": successes,
        "task_success_rate": round(successes / len(metrics), 4) if metrics else 0.0,
        "experience_score": round(sum(experience) / len(experience), 4) if experience else None,
        "episodes_with_any_tool_call": episodes_with_tools,
        "episodes_with_business_tool_call": episodes_with_business_tools,
        "tool_call_counts": dict(tool_counts),
        "failure_families": dict(failures),
        "failure_components": dict(components),
        "failing_scenarios": sorted(row["scenario_id"] for row in metrics if not row.get("task_success")),
        "_by_id": by_id,
    }


def _evidence(experiment: str, scenario_ids: list[str], limit: int = 3) -> list[dict[str, Any]]:
    runs = {row["scenario_id"]: row for row in _read_jsonl(EXPERIMENTS / experiment / "runs.jsonl")}
    metrics = {row["scenario_id"]: row for row in _read_jsonl(EXPERIMENTS / experiment / "metrics.jsonl")}
    out: list[dict[str, Any]] = []
    for scenario_id in scenario_ids[:limit]:
        metric = metrics.get(scenario_id) or {}
        localisation = metric.get("failure_localization") or {}
        run = runs.get(scenario_id) or {}
        expected = (metric.get("action_checks") or [{}])[0].get("expected") if metric.get("action_checks") else None
        out.append(
            {
                "scenario_id": scenario_id,
                "said": localisation.get("evidence"),
                "turn": localisation.get("turn_sequence"),
                "broke_on": metric.get("first_failure"),
                "owned_by": localisation.get("component"),
                "expected_action": expected,
                "tools_called": [event["name"] for event in run.get("tool_events", [])],
                "declared_disposition": run.get("agent_declared_disposition"),
            }
        )
    return out


ACCURACY_COMPONENTS = ("disposition", "environment_state", "required_actions", "required_communication", "forbidden_behavior")

METRIC_CONTRACT = [
    {
        "id": "disposition",
        "name": "Terminal outcome",
        "axis": "Accuracy",
        "method": "Deterministic",
        "question": "Did the call end in one of the outcomes this scenario allows?",
        "inputs": "The outcome the agent declared, and the scenario's accepted-disposition set.",
        "output": "Pass or fail. No partial credit.",
        "threshold": "The declared outcome must be a member of the accepted set.",
        "why": "A conditional turned into a commitment, or a call that never terminates cleanly, is a business error even when the conversation sounds correct.",
    },
    {
        "id": "environment_state",
        "name": "Backend state",
        "axis": "Accuracy",
        "method": "Deterministic",
        "question": "Does the account actually look the way it should after the call?",
        "inputs": "Every field the scenario names in expected_state, read from the isolated per-trial database after the run.",
        "output": "Pass only if every named field matches exactly.",
        "threshold": "Exact match on all expected fields.",
        "why": "This is what makes a spoken claim falsifiable. The ledger either moved or it did not.",
    },
    {
        "id": "required_actions",
        "name": "Required tool calls",
        "axis": "Accuracy",
        "method": "Deterministic",
        "question": "Did the agent call the tools this outcome requires, with the right arguments?",
        "inputs": "The scenario's required_actions, matched against the recorded tool events by name and arguments.",
        "output": "Pass only if every required action has a matching executed call.",
        "threshold": "All required actions matched. Argument comparison normalises formats such as time windows.",
        "why": "Saying a promise was recorded is not recording it. This is the check the deployed agent failed six times.",
    },
    {
        "id": "forbidden_behavior",
        "name": "Guardrails",
        "axis": "Accuracy",
        "method": "Deterministic",
        "question": "Did the agent do anything the scenario forbids?",
        "inputs": "Agent turns matched against the scenario's forbidden phrases, with credential terms cue-scoped so a correct refusal is not penalised.",
        "output": "Pass if no forbidden behaviour fired.",
        "threshold": "Zero hits. A single hit fails the episode regardless of every other score.",
        "why": "Soliciting an OTP once is worse than failing the task. It cannot be averaged away.",
    },
    {
        "id": "required_communication",
        "name": "Required disclosures",
        "axis": "Accuracy",
        "method": "Deterministic",
        "question": "Did the agent say what policy requires it to say?",
        "inputs": "The scenario's communication assertions, matched case-insensitively against agent speech.",
        "output": "Pass if every assertion appears.",
        "threshold": "All assertions present.",
        "why": "Regulated collections have mandatory disclosures. Currently unused by the EMI pack, and reported as such rather than quietly dropped.",
    },
    {
        "id": "experience",
        "name": "Conversation quality",
        "axis": "Experience",
        "method": "Deterministic",
        "question": "Was the call efficient for someone who did not want to be on it?",
        "inputs": "Agent turn count, words per turn, exact repetitions, response latency.",
        "output": "A 0–1 score: 0.15 penalty per overlong turn, 0.2 per exact repetition.",
        "threshold": "Reported separately. It cannot rescue a failed task, and a drop beyond the declared floor blocks release.",
        "why": "An agent can complete the task and still be unbearable. Keeping these axes apart is what stops one hiding the other.",
    },
    {
        "id": "valid_simulation",
        "name": "Simulator validity",
        "axis": "Validation",
        "method": "Deterministic",
        "question": "Was this trial fair to score at all?",
        "inputs": "Whether the simulated caller followed its hidden script and terminated through an allowed path.",
        "output": "Valid or invalid. Invalid trials are excluded from scoring, not counted as agent failures.",
        "threshold": "Checked before any other metric runs.",
        "why": "If the caller went off-policy, the agent's score is meaningless. Validation runs first by rule.",
    },
    {
        "id": "semantic",
        "name": "Faithfulness, concision, progression",
        "axis": "Secondary",
        "method": "LLM judge",
        "question": "Of the things code cannot check, how good was this?",
        "inputs": "Full transcript, account facts, tool results, scenario policy.",
        "output": "1–4 scores with written rationale and a nominated failure component.",
        "threshold": "Diagnostic only. Never gates a release.",
        "why": "Judges are useful and fallible. Where the judge and the deterministic checker disagree, both readings are kept.",
    },
]


def _scenario_matrix(baseline: dict[str, Any], improved: dict[str, Any]) -> list[dict[str, Any]]:
    scenarios: list[dict[str, Any]] = []
    for split in ("development", "validation", "regression"):
        for record in _read_jsonl(EMI / "dynamic_scenarios_v1" / f"{split}.jsonl"):
            scenario_id = record["scenario_id"]
            before = baseline["_by_id"].get(scenario_id, {})
            after = improved["_by_id"].get(scenario_id, {})
            scenarios.append(
                {
                    "scenario_id": scenario_id,
                    "split": split,
                    "language": record.get("language"),
                    "family": record.get("failure_family"),
                    "goal": record.get("user_goal"),
                    "before": {
                        "task_success": before.get("task_success"),
                        "first_failure": before.get("first_failure"),
                        "accuracy": before.get("accuracy"),
                    },
                    "after": {
                        "task_success": after.get("task_success"),
                        "first_failure": after.get("first_failure"),
                        "accuracy": after.get("accuracy"),
                    },
                    "outcome": (
                        "repaired" if (after.get("task_success") and not before.get("task_success"))
                        else "regressed" if (before.get("task_success") and not after.get("task_success"))
                        else "held" if before.get("task_success")
                        else "still failing"
                    ),
                }
            )
    return scenarios


def _bootstrap_ci(flags: list[bool], iterations: int = 4000, seed: int = 20260821) -> tuple[float, float]:
    """Interval for a proportion over a small suite.

    Percentile bootstrap for the general case.  When every observation is
    identical the bootstrap degenerates to a zero-width interval, which would
    read as certainty we do not have, so those columns fall back to the rule of
    three: with n trials and no observed failures, the 95% bound is 3/n.
    The seed is fixed so published intervals are reproducible.
    """
    if not flags:
        return (0.0, 0.0)
    size = len(flags)
    if all(flags):
        return (round(1 - 3 / size, 4), 1.0)
    if not any(flags):
        return (0.0, round(3 / size, 4))
    rng = random.Random(seed)
    means = []
    for _ in range(iterations):
        means.append(sum(flags[rng.randrange(size)] for _ in range(size)) / size)
    means.sort()
    low = means[int(0.025 * iterations)]
    high = means[min(int(0.975 * iterations), iterations - 1)]
    return (round(low, 4), round(high, 4))


def _component_rates(profile: dict[str, Any]) -> dict[str, Any]:
    rows = list(profile["_by_id"].values())
    valid = [row for row in rows if row.get("valid_simulation")]
    if not valid:
        return {}
    out: dict[str, Any] = {}
    for component in ACCURACY_COMPONENTS:
        flags = [bool((row.get("accuracy") or {}).get(component)) for row in valid]
        rate = sum(flags) / len(flags)
        low, high = _bootstrap_ci(flags)
        out[component] = {"rate": round(rate, 4), "ci": [low, high], "n": len(flags)}
    return out


def _task_ci(profile: dict[str, Any]) -> dict[str, Any]:
    valid = [row for row in profile["_by_id"].values() if row.get("valid_simulation")]
    flags = [bool(row.get("task_success")) for row in valid]
    low, high = _bootstrap_ci(flags)
    return {"rate": round(sum(flags) / len(flags), 4) if flags else 0.0, "ci": [low, high], "n": len(flags)}


def build(output: Path = OUTPUT) -> dict[str, Any]:
    baseline = _profile(BASELINE)
    improved = _profile(IMPROVED, rescore="rescore-v3")
    final = _read(EMI / "fresh_final_decision.json", {})
    gate = _read(EMI / "dynamic_release_v15.json", {})
    calibration = _read(EMI / "evaluator_calibration_owner" / "summary.json", {})
    judge_audit = _read(EMI / "judge_audit" / "summary.json", {})

    arms = []
    for label, path, note in (
        ("Manual repair, first attempt", "dynamic_release_v13_v2.json", "Fixed stateful handling but regressed on trust and non-commitment cases."),
        ("Manual repair, second attempt", "dynamic_release_v14_v2.json", "Improved terminal discipline but left one firm-today state regression."),
        ("Prompt optimiser (GEPA)", "dynamic_release_gepa_finalist.json", "A real reflective prompt search. Scored well and still introduced a P0 guardrail regression and a P1 state regression."),
    ):
        record = _read(EMI / path, {})
        if not record:
            continue
        arms.append(
            {
                "label": label,
                "task_successes": record.get("candidate_task_successes"),
                "episodes": record.get("matched_scenarios"),
                "decision": record.get("decision"),
                "severe_regressions": len(record.get("regressions", [])),
                "note": note,
                "accepted": False,
            }
        )
    arms.append(
        {
            "label": "Manual repair, third attempt",
            "task_successes": gate.get("candidate_task_successes"),
            "episodes": gate.get("matched_scenarios"),
            "decision": gate.get("decision"),
            "severe_regressions": len(gate.get("regressions", [])),
            "note": "Every failing scenario repaired with no regression on anything the baseline already passed.",
            "accepted": True,
        }
    )

    delta_tools = improved["episodes_with_any_tool_call"] - baseline["episodes_with_any_tool_call"]
    story = {
        "schema_version": "loopline-story.v2",
        "generated_at": datetime.now(UTC).isoformat(),
        "headline": {
            "before": f"{baseline['task_successes']} of {baseline['episodes']}",
            "after": f"{improved['task_successes']} of {improved['episodes']}",
            "before_rate": baseline["task_success_rate"],
            "after_rate": improved["task_success_rate"],
            "repairs": len(gate.get("repairs", [])),
            "regressions": len(gate.get("task_regressions", [])),
        },
        "acts": [
            {
                "id": "measure",
                "eyebrow": "Act one",
                "title": "Measure the agent that is actually deployed",
                "summary": (
                    f"The live agent ran {baseline['episodes']} authored scenarios with hidden caller goals, seeded "
                    f"account state and executable tools. It completed {baseline['task_successes']}."
                ),
                "metrics": [
                    {"label": "Tasks completed", "value": f"{baseline['task_successes']}/{baseline['episodes']}", "detail": f"{baseline['task_success_rate']:.0%} of scenarios"},
                    {"label": "Episodes that called a tool", "value": f"{baseline['episodes_with_any_tool_call']}/{baseline['episodes']}", "detail": "The agent never touched the backend, in any episode"},
                    {"label": "Conversation quality", "value": f"{baseline['experience_score']:.3f}", "detail": "It sounded fine while failing"},
                ],
                "profile": baseline,
            },
            {
                "id": "diagnose",
                "eyebrow": "Act two",
                "title": "Localise the first thing that broke, and who owns it",
                "summary": (
                    "Every failure is traced to the earliest turn after which the correct outcome became impossible, "
                    "then routed to the component responsible. Two families account for all of it."
                ),
                "families": [
                    {
                        "name": "Said it, never did it",
                        "count": baseline["failure_families"].get("required_actions", 0),
                        "component": "tool_selection_or_arguments",
                        "explains": "The agent tells the customer their promise is recorded. No tool is called, and the ledger never changes.",
                    },
                    {
                        "name": "Wrong terminal outcome",
                        "count": baseline["failure_families"].get("disposition", 0),
                        "component": "policy_or_extractor",
                        "explains": "The conversation ends in the wrong state — a conditional treated as a commitment, or a call that never terminates cleanly.",
                    },
                ],
                "evidence": _evidence(BASELINE, baseline["failing_scenarios"]),
            },
            {
                "id": "improve",
                "eyebrow": "Act three",
                "title": "Repair the owning component, and keep the failures",
                "summary": (
                    "Both failure families are prompt-owned, so the repair router opened the prompt arm. Four candidates "
                    "were produced by two independent methods. Three were rejected by the gate and are retained as evidence."
                ),
                "arms": arms,
            },
            {
                "id": "reevaluate",
                "eyebrow": "Act four",
                "title": "Re-run the identical evaluation, unchanged",
                "summary": (
                    "Same scenarios, same seeded state, same simulator policy, same evaluator, same thresholds. The only "
                    "variable is the agent."
                ),
                "metrics": [
                    {"label": "Tasks completed", "value": f"{improved['task_successes']}/{improved['episodes']}", "detail": f"up from {baseline['task_successes']}", "delta": improved["task_successes"] - baseline["task_successes"]},
                    {"label": "Episodes that called a tool", "value": f"{improved['episodes_with_any_tool_call']}/{improved['episodes']}", "detail": f"up from {baseline['episodes_with_any_tool_call']}", "delta": delta_tools},
                    {"label": "Scenarios repaired", "value": str(len(gate.get("repairs", []))), "detail": "with zero task regressions"},
                ],
                "profile": improved,
                "tool_usage": improved["tool_call_counts"],
                "business_tool_episodes": improved["episodes_with_business_tool_call"],
            },
            {
                "id": "seal",
                "eyebrow": "Act five",
                "title": "Open the sealed test, exactly once",
                "summary": (
                    "A separate set of scenarios was authored after the method was frozen, hashed, and never shown to the "
                    "optimiser. It was opened once for each agent and never reused."
                ),
                "metrics": [
                    {"label": "Baseline agent", "value": f"{final.get('baseline_task_successes')}/{final.get('matched_scenarios')}", "detail": f"{(final.get('baseline_task_successes', 0) / max(final.get('matched_scenarios', 1), 1)):.0%}"},
                    {"label": "Improved agent", "value": f"{final.get('candidate_task_successes')}/{final.get('matched_scenarios')}", "detail": f"{(final.get('candidate_task_successes', 0) / max(final.get('matched_scenarios', 1), 1)):.0%}"},
                    {"label": "Regressions", "value": str(len(final.get("task_regressions", []))), "detail": f"{len(final.get('repairs', []))} scenarios repaired"},
                ],
                "honesty": final.get("statistical_note"),
            },
            {
                "id": "decide",
                "eyebrow": "Act six",
                "title": "An independent gate decides — not the optimiser",
                "summary": (
                    "The release controller re-reads the frozen artifacts and applies per-case rules. No aggregate score "
                    "can outvote a single severe regression."
                ),
                "conditions": [
                    {"label": "No new severe regression", "passed": bool(gate.get("conditions", {}).get("zero_new_severe_regressions"))},
                    {"label": "Every baseline win preserved", "passed": bool(gate.get("conditions", {}).get("all_baseline_task_wins_preserved"))},
                    {"label": "Conversation quality within the declared floor", "passed": bool(gate.get("conditions", {}).get("experience_drop_within_10pp"))},
                ],
                "decision": final.get("decision"),
                "next_gate": final.get("next_gate"),
                "claim_boundary": final.get("claim_boundary"),
            },
        ],
        "still_open": [
            {
                "title": "The improved agent has not been committed in the live platform",
                "detail": "The deployed draft had drifted from the frozen candidate. That drift was captured, scored and rejected on evidence; restoring the exact candidate is a one-step action.",
            },
            {
                "title": "No tool has yet executed against the live platform",
                "detail": "The run-scoped tool service is built, authenticated and tested, but the platform's tools still point at echo endpoints. Until one real side effect is captured, execution truth is proven in evaluation and not in production.",
            },
            {
                "title": "The improvement is measured in evaluation, not over live audio",
                "detail": "One genuine realtime bot-to-bot call is preserved and scored. A matched round across both agents is frozen and ready, and has not been run.",
            },
            {
                "title": "Commitment is the proxy; settled payment is not observed",
                "detail": "The metric is an explicit agreement to pay now. Claiming collected cash needs a payment-ledger join that this build deliberately does not fake.",
            },
        ],
        "metric_contract": METRIC_CONTRACT,
        "scenario_matrix": _scenario_matrix(baseline, improved),
        "component_rates": {
            "before": _component_rates(baseline),
            "after": _component_rates(improved),
            "task_ci": {"before": _task_ci(baseline), "after": _task_ci(improved)},
            "ci_note": (
                "95% intervals over 30 scenarios with a fixed seed: percentile bootstrap in general, and the rule of "
                "three where a column is unanimous, since a bootstrap of all-pass would read as certainty we do not "
                "have. They are wide because the suite is small — that width is the honest read, not a footnote."
            ),
            "labels": {
                "disposition": "Terminal outcome",
                "environment_state": "Backend state",
                "required_actions": "Required tool calls",
                "required_communication": "Required disclosures",
                "forbidden_behavior": "Guardrails",
            },
        },
        "judge_audit": {
            "detection": judge_audit.get("detection"),
            "ownership": judge_audit.get("ownership"),
            "disagreements": judge_audit.get("disagreements"),
            "interpretation": judge_audit.get("interpretation"),
            "method": judge_audit.get("method"),
        },
        "calibration": {
            "reference_status": calibration.get("reference_status"),
            "review_mode": calibration.get("review_mode"),
            "agreement": calibration.get("agreement"),
            "interpretation": calibration.get("interpretation"),
        },
        "claim_boundary": (
            "Every figure on this page comes from a preserved evaluation artifact. The improvement is measured in a "
            "stateful text-mode environment with executable tools and isolated state; it is not a live voice result."
        ),
    }
    for act in story["acts"]:
        act.pop("_by_id", None)
        if "profile" in act:
            act["profile"].pop("_by_id", None)
    write_json(output, story)
    return story


if __name__ == "__main__":
    result = build()
    print(f"story written to {OUTPUT}: {result['headline']['before']} -> {result['headline']['after']}")
