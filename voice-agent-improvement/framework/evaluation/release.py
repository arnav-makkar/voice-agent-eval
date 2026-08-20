"""Strict paired release gate for stateful dynamic evaluations."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from framework.core.io import read_jsonl, write_json


SEVERE_COMPONENTS = {"forbidden_behavior", "environment_state", "required_actions"}
MAX_EXPERIENCE_DROP = 0.10


def _exact_paired_p(repairs: int, task_regressions: int) -> float | None:
    """Two-sided exact McNemar/binomial diagnostic over discordant pairs."""
    discordant = repairs + task_regressions
    if discordant == 0:
        return None
    tail = sum(math.comb(discordant, index) for index in range(min(repairs, task_regressions) + 1)) / (2**discordant)
    return round(min(1.0, 2 * tail), 8)


def decide(baseline_path: Path, candidate_path: Path, output: Path) -> dict[str, Any]:
    baseline = {item["scenario_id"]: item for item in read_jsonl(baseline_path)}
    candidate = {item["scenario_id"]: item for item in read_jsonl(candidate_path)}
    if set(baseline) != set(candidate):
        raise ValueError("paired release gate requires identical scenario IDs")
    regressions = []
    repairs = []
    task_regression_ids = []
    for scenario_id in sorted(baseline):
        before = baseline[scenario_id]
        after = candidate[scenario_id]
        if before["task_success"] and not after["task_success"]:
            task_regression_ids.append(scenario_id)
            regressions.append({"scenario_id": scenario_id, "type": "task_regression", "severity": "P1", "evidence": after.get("failure_localization")})
        for component in SEVERE_COMPONENTS:
            if before["accuracy"].get(component, True) and not after["accuracy"].get(component, True):
                regressions.append({"scenario_id": scenario_id, "type": f"{component}_regression", "severity": "P0" if component == "forbidden_behavior" else "P1", "evidence": after.get("failure_localization")})
        if before["valid_simulation"] and not after["valid_simulation"]:
            regressions.append({"scenario_id": scenario_id, "type": "simulator_validity_regression", "severity": "P1", "evidence": after.get("failure_localization")})
        if not before["task_success"] and after["task_success"]:
            repairs.append(scenario_id)
    before_success = sum(item["task_success"] for item in baseline.values())
    after_success = sum(item["task_success"] for item in candidate.values())
    before_experience = sum(item["experience"]["score"] for item in baseline.values()) / len(baseline)
    after_experience = sum(item["experience"]["score"] for item in candidate.values()) / len(candidate)
    experience_drop = before_experience - after_experience
    experience_floor_pass = experience_drop <= MAX_EXPERIENCE_DROP
    route_a = after_success > before_success and not regressions and experience_floor_pass
    route_b = after_success == before_success and after_experience > before_experience and not regressions
    decision = "reject_new_severe_regression" if regressions else "eligible_for_fresh_final_test" if route_a or route_b else "hold_no_predeclared_improvement_route"
    record = {
        "schema_version": "dynamic-release-decision.v1",
        "decision": decision,
        "matched_scenarios": len(baseline),
        "baseline_task_successes": before_success,
        "candidate_task_successes": after_success,
        "baseline_experience": round(before_experience, 4),
        "candidate_experience": round(after_experience, 4),
        "repairs": repairs,
        "task_regressions": task_regression_ids,
        "regressions": regressions,
        "routes": {"more_task_wins": route_a, "task_non_degradation_plus_experience": route_b},
        "conditions": {
            "zero_new_severe_regressions": not regressions,
            "all_baseline_task_wins_preserved": not task_regression_ids,
            "experience_drop_within_10pp": experience_floor_pass,
        },
        "paired_task_evidence": {
            "repairs": len(repairs),
            "task_regressions": len(task_regression_ids),
            "discordant_pairs": len(repairs) + len(task_regression_ids),
            "exact_two_sided_p": _exact_paired_p(len(repairs), len(task_regression_ids)),
            "interpretation": "Exact paired task-outcome diagnostic; promotion still depends on per-case gates and the fresh final test.",
        },
        "thresholds": {"maximum_experience_drop": MAX_EXPERIENCE_DROP},
        "next_gate": "fresh_group_separated_final_test" if decision == "eligible_for_fresh_final_test" else None,
        "claim_boundary": "Paired development/validation/regression decision. The exact p-value is diagnostic and does not replace fresh final or matched voice evidence.",
    }
    write_json(output, record)
    return record


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(decide(args.baseline, args.candidate, args.output), indent=2))
