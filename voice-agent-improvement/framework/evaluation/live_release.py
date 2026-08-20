"""Exact matched release gate for EVA–Samvaad live suites."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from statistics import mean
from typing import Any


COMPONENTS = (
    "task_completion",
    "faithfulness",
    "agent_speech_fidelity",
    "turn_taking",
    "conciseness",
    "conversation_progression",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _metric(metrics: dict[str, Any], name: str) -> float | None:
    raw = (metrics.get("metrics") or {}).get(name)
    if not isinstance(raw, dict):
        return None
    value = raw.get("normalized_score", raw.get("score"))
    return float(value) if isinstance(value, (int, float)) else None


def _record_key(relative: Path) -> tuple[str, int]:
    parts = relative.parts
    if len(parts) >= 2 and parts[1].startswith("trial_"):
        return parts[0], int(parts[1].removeprefix("trial_"))
    return parts[0], 0


def load_live_suite(run_dir: Path) -> dict[tuple[str, int], dict[str, Any]]:
    rows: dict[tuple[str, int], dict[str, Any]] = {}
    records_root = run_dir / "records"
    for metrics_path in records_root.glob("**/metrics.json"):
        relative = metrics_path.parent.relative_to(records_root)
        if "failed_attempt" in str(relative):
            continue
        record_id, trial = _record_key(relative)
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        result_path = metrics_path.parent / "result.json"
        result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {}
        rows[(record_id, trial)] = {
            "record_id": record_id,
            "trial": trial,
            "metrics": {name: _metric(metrics, name) for name in COMPONENTS},
            "aggregate": dict(metrics.get("aggregate_metrics") or {}),
            "completed": bool(result.get("completed")),
            "record_directory": str(metrics_path.parent),
            "metrics_sha256": _sha(metrics_path),
        }
    return rows


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    component_means = {}
    for name in COMPONENTS:
        values = [row["metrics"][name] for row in rows if row["metrics"].get(name) is not None]
        component_means[name] = mean(values) if values else None
    tasks = [row["metrics"]["task_completion"] == 1.0 for row in rows]
    accuracy_passes = [
        all(row["metrics"].get(name) == 1.0 for name in ("task_completion", "faithfulness", "agent_speech_fidelity"))
        for row in rows
    ]
    experience_passes = [
        all(row["metrics"].get(name) == 1.0 for name in ("turn_taking", "conciseness", "conversation_progression"))
        for row in rows
    ]
    return {
        "trials": len(rows),
        "task_wins": sum(tasks),
        "task_rate": mean(tasks) if tasks else None,
        "accuracy_passes": sum(accuracy_passes),
        "experience_passes": sum(experience_passes),
        "component_means": component_means,
    }


def compare_live_suites(baseline_dir: Path, candidate_dir: Path) -> dict[str, Any]:
    baseline = load_live_suite(baseline_dir)
    candidate = load_live_suite(candidate_dir)
    matched = sorted(set(baseline) & set(candidate))
    if not matched:
        raise ValueError("no matched record/trial pairs")
    if set(baseline) != set(candidate):
        raise ValueError(
            f"suite mismatch: baseline_only={sorted(set(baseline)-set(candidate))}, "
            f"candidate_only={sorted(set(candidate)-set(baseline))}"
        )

    pairs = []
    task_repairs = []
    task_regressions = []
    new_p0 = []
    for key in matched:
        b = baseline[key]
        c = candidate[key]
        b_task = b["metrics"]["task_completion"] == 1.0
        c_task = c["metrics"]["task_completion"] == 1.0
        if not b_task and c_task:
            task_repairs.append(key)
        if b_task and not c_task:
            task_regressions.append(key)
        for metric in ("faithfulness", "agent_speech_fidelity"):
            if b["metrics"].get(metric) == 1.0 and c["metrics"].get(metric) == 0.0:
                new_p0.append((*key, metric))
        pairs.append(
            {
                "record_id": key[0],
                "trial": key[1],
                "baseline": b,
                "candidate": c,
                "task_delta": int(c_task) - int(b_task),
                "experience_delta": mean(
                    c["metrics"][name] - b["metrics"][name]
                    for name in ("turn_taking", "conciseness", "conversation_progression")
                    if c["metrics"].get(name) is not None and b["metrics"].get(name) is not None
                ),
            }
        )

    baseline_summary = _summary([baseline[key] for key in matched])
    candidate_summary = _summary([candidate[key] for key in matched])
    no_hard_regression = not task_regressions and not new_p0
    business_win = candidate_summary["task_wins"] > baseline_summary["task_wins"]
    task_non_degradation = candidate_summary["task_wins"] == baseline_summary["task_wins"]
    quality_win = candidate_summary["experience_passes"] > baseline_summary["experience_passes"]
    if no_hard_regression and business_win:
        decision = "promote_business_win_route"
    elif no_hard_regression and task_non_degradation and quality_win:
        decision = "promote_quality_route_no_tsr_claim"
    else:
        decision = "hold"
    return {
        "schema_version": "matched-live-release.v1",
        "decision": decision,
        "matched_trials": len(matched),
        "baseline": baseline_summary,
        "candidate": candidate_summary,
        "task_repairs": [{"record_id": key[0], "trial": key[1]} for key in task_repairs],
        "task_regressions": [{"record_id": key[0], "trial": key[1]} for key in task_regressions],
        "new_p0": [{"record_id": key[0], "trial": key[1], "metric": key[2]} for key in new_p0],
        "routes": {
            "business_win": business_win,
            "task_non_degradation": task_non_degradation,
            "quality_win": quality_win,
            "no_hard_regression": no_hard_regression,
        },
        "pairs": pairs,
        "claim_boundary": (
            "A business-win route supports matched voice task lift. A quality route supports only task "
            "non-degradation plus experience improvement. Neither proves cash collection or production scale."
        ),
    }

