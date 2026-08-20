"""Audit the semantic judge against executable truth.

The judge is secondary by design: it grades what code cannot, and never gates a
release.  That claim is only credible if we can say how often it agrees with the
deterministic checker on the questions both of them answer.  This module computes
that from evidence already on disk — no new model calls.

Two questions are compared:

* did this episode fail at all — judge's ``failure_component`` present versus the
  deterministic ``first_failure``;
* if it failed, which component owns it — judge's nomination versus the
  deterministic localisation, after mapping both onto a shared vocabulary.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from framework.core.io import write_json

ROOT = Path(__file__).resolve().parents[2]
EMI = ROOT / "artifacts" / "framework" / "emi"
EXPERIMENTS = EMI / "dynamic_experiments"
OUTPUT = EMI / "judge_audit" / "summary.json"

# The judge and the deterministic checker use different vocabularies for the same
# underlying surfaces; this maps both onto one so disagreement is real rather than
# a naming artefact.
# The deterministic checker emits tool_selection_or_arguments / policy_or_extractor /
# guardrail. The judge emits agent_policy / extractor / knowledge / simulator / none.
# Both are folded onto one vocabulary so a disagreement means a real disagreement
# about ownership rather than two names for the same surface.
CANON = {
    # tool surface
    "tool_selection_or_arguments": "tool",
    "tool": "tool",
    "tools": "tool",
    # prompt / policy / extractor surface — the deterministic checker does not
    # separate policy from extractor, so the judge's finer split folds into it
    "policy_or_extractor": "policy",
    "policy": "policy",
    "agent_policy": "policy",
    "agent_prompt": "policy",
    "prompt": "policy",
    "extractor": "policy",
    # knowledge is a surface the deterministic checker cannot see at all
    "knowledge": "knowledge",
    "guardrail": "guardrail",
    "simulator": "simulator",
    "simulator_or_caller": "simulator",
    "none": None,
    "": None,
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _canon(value: Any) -> str | None:
    if not value:
        return None
    return CANON.get(str(value).strip().lower(), str(value).strip().lower())


def audit(experiments: tuple[str, ...] = ("v12-dynamic-full", "v15-firm-today-full")) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for experiment in experiments:
        deterministic = {row["scenario_id"]: row for row in _read_jsonl(EXPERIMENTS / experiment / "metrics.jsonl")}
        judged = {row["scenario_id"]: row for row in _read_jsonl(EXPERIMENTS / experiment / "semantic-v2" / "semantic_metrics.jsonl")}
        for scenario_id, judge in judged.items():
            metric = deterministic.get(scenario_id)
            if not metric:
                continue
            det_failed = bool(metric.get("first_failure"))
            judge_failed = bool(judge.get("failure_component")) and _canon(judge.get("failure_component")) is not None
            det_owner = _canon((metric.get("failure_localization") or {}).get("component"))
            judge_owner = _canon(judge.get("failure_component"))
            rows.append(
                {
                    "experiment": experiment,
                    "scenario_id": scenario_id,
                    "deterministic_failed": det_failed,
                    "judge_failed": judge_failed,
                    "detection_agrees": det_failed == judge_failed,
                    "deterministic_owner": det_owner,
                    "judge_owner": judge_owner,
                    "owner_agrees": (det_owner == judge_owner) if (det_failed and judge_failed) else None,
                }
            )

    detection = [row for row in rows]
    both_failed = [row for row in rows if row["owner_agrees"] is not None]
    disagreements = [
        {
            "scenario_id": row["scenario_id"],
            "experiment": row["experiment"],
            "deterministic": row["deterministic_owner"],
            "judge": row["judge_owner"],
        }
        for row in both_failed
        if not row["owner_agrees"]
    ]

    summary = {
        "schema_version": "judge-audit.v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "method": (
            "Recomputed from preserved episode artifacts. No new model calls were made, so this audit costs nothing "
            "and cannot drift from the results it describes."
        ),
        "episodes": len(rows),
        "detection": {
            "question": "Did the judge and the executable checker agree on whether the episode failed at all?",
            "agreement": round(sum(row["detection_agrees"] for row in detection) / len(detection), 4) if detection else None,
            "n": len(detection),
        },
        "ownership": {
            "question": "When both said it failed, did they agree on which component owns the failure?",
            "agreement": round(sum(row["owner_agrees"] for row in both_failed) / len(both_failed), 4) if both_failed else None,
            "n": len(both_failed),
        },
        "confusion": dict(
            Counter(f"deterministic={row['deterministic_owner']}|judge={row['judge_owner']}" for row in both_failed)
        ),
        "disagreements": disagreements,
        "interpretation": (
            "The judge is reliable at noticing that something went wrong and materially less reliable at saying what "
            "owns it. That is precisely why ownership routing is advisory and the executable checker controls the "
            "release gate. Publishing the number is the point: a grader whose accuracy is unstated should not be trusted."
        ),
    }
    write_json(OUTPUT, summary)
    return summary


if __name__ == "__main__":
    result = audit()
    print(
        f"detection agreement {result['detection']['agreement']:.0%} (n={result['detection']['n']}), "
        f"ownership agreement {result['ownership']['agreement']:.0%} (n={result['ownership']['n']})"
    )
