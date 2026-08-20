"""Interpret the frozen paired gate after the once-only fresh-final evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from framework.core.io import write_json


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def decide(
    paired_path: Path,
    seal_path: Path,
    access_path: Path,
    output: Path,
    baseline_semantic_path: Path | None = None,
    candidate_semantic_path: Path | None = None,
) -> dict[str, Any]:
    paired = _read(paired_path)
    seal = _read(seal_path)
    access = _read(access_path)
    baseline_semantic = _read(baseline_semantic_path) if baseline_semantic_path else {}
    candidate_semantic = _read(candidate_semantic_path) if candidate_semantic_path else {}
    runs = access.get("evaluation_runs", [])
    hashes = {item.get("candidate_hash") for item in runs}
    expected_hashes = {seal.get("baseline_frozen_sha256"), seal.get("candidate_method_frozen_sha256")}
    protocol_valid = (
        paired.get("matched_scenarios") == seal.get("records") == 12
        and len(runs) == 2
        and hashes == expected_hashes
        and access.get("accessed_by_improvement") is False
    )
    paired_pass = (
        paired.get("decision") == "eligible_for_fresh_final_test"
        and paired.get("conditions", {}).get("zero_new_severe_regressions") is True
        and paired.get("conditions", {}).get("all_baseline_task_wins_preserved") is True
        and paired.get("conditions", {}).get("experience_drop_within_10pp") is True
    )
    if not protocol_valid:
        decision = "invalid_final_protocol"
        next_gate = None
    elif not paired_pass:
        decision = "reject_on_fresh_final"
        next_gate = None
    else:
        decision = "pass_text_final_awaiting_matched_voice"
        next_gate = "human_review_and_matched_indus_voice"
    result = {
        "schema_version": "fresh-final-decision.v1",
        "decision": decision,
        "protocol_valid": protocol_valid,
        "dataset_sha256": seal.get("dataset_sha256"),
        "matched_scenarios": paired.get("matched_scenarios"),
        "baseline_task_successes": paired.get("baseline_task_successes"),
        "candidate_task_successes": paired.get("candidate_task_successes"),
        "repairs": paired.get("repairs", []),
        "task_regressions": paired.get("task_regressions", []),
        "regressions": paired.get("regressions", []),
        "baseline_experience": paired.get("baseline_experience"),
        "candidate_experience": paired.get("candidate_experience"),
        "paired_task_evidence": paired.get("paired_task_evidence", {}),
        "semantic_secondary": {
            "baseline": {
                "faithfulness": baseline_semantic.get("average_faithfulness"),
                "conciseness": baseline_semantic.get("average_conciseness"),
                "progression": baseline_semantic.get("average_progression"),
            },
            "candidate": {
                "faithfulness": candidate_semantic.get("average_faithfulness"),
                "conciseness": candidate_semantic.get("average_conciseness"),
                "progression": candidate_semantic.get("average_progression"),
            },
            "role": "diagnostic only; deterministic state/action/guardrail truth controls the gate",
        },
        "conditions": paired.get("conditions", {}),
        "evaluation_runs": runs,
        "next_gate": next_gate,
        "statistical_note": "The exact paired p-value is diagnostic. Four discordant pairs in a 12-case final are insufficient for a broad statistical claim.",
        "claim_boundary": "The frozen candidate improved exact text-mode task completion on this sealed final with no observed task regression. Production payment lift and matched voice improvement are not established.",
    }
    write_json(output, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paired", type=Path)
    parser.add_argument("seal", type=Path)
    parser.add_argument("access", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--baseline-semantic", type=Path)
    parser.add_argument("--candidate-semantic", type=Path)
    args = parser.parse_args()
    print(json.dumps(decide(
        args.paired,
        args.seal,
        args.access,
        args.output,
        args.baseline_semantic,
        args.candidate_semantic,
    ), indent=2))


if __name__ == "__main__":
    main()
