"""Episodic memory: turn confirmed failures into durable, inspectable lessons.

Prompt repair rewrites the whole instruction and hopes the change generalises.  A
lesson store does something narrower and more auditable: for each failure family
the loop has actually confirmed, it keeps one short rule derived from real
evidence, and injects only the lessons relevant to the scenario being run.

Three properties make this safe to put in a governed loop:

* a lesson is only minted from a failure the deterministic checker confirmed, so
  the judge cannot invent one;
* every lesson carries the episodes it came from, so it can be audited or revoked;
* lessons are versioned and gated exactly like a prompt candidate — injecting them
  produces a new candidate that must pass the same frozen evaluation.

This is deliberately not a vector store.  At this scale the useful memory is a
handful of specific rules a human can read and disagree with.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from framework.core.io import write_json

ROOT = Path(__file__).resolve().parents[2]
EMI = ROOT / "artifacts" / "framework" / "emi"
EXPERIMENTS = EMI / "dynamic_experiments"
OUTPUT = EMI / "lessons" / "lessons.v1.json"

# What a confirmed failure of each kind teaches, phrased as an instruction the agent
# can act on.  The mapping is authored once and reviewed; the *evidence* for whether
# a lesson applies comes from the evaluation, never from a model.
LESSON_TEMPLATES: dict[str, dict[str, str]] = {
    "required_actions": {
        "rule": (
            "Before closing on an outcome that requires a recorded effect, call the matching tool and wait for its "
            "result. Saying an outcome was recorded does not record it."
        ),
        "why": "Episodes where the agent announced a promise or callback and wrote nothing to the ledger.",
    },
    "disposition": {
        "rule": (
            "Close on exactly one allowed outcome, and only once the caller's own words support it. A conditional, a "
            "hedge, or a bare acknowledgement is not a commitment."
        ),
        "why": "Episodes that ended in the wrong terminal state, usually by upgrading a conditional into a commitment.",
    },
    "environment_state": {
        "rule": "Leave the account in the state the outcome implies. If the state cannot be reached, close on the outcome that is actually true.",
        "why": "Episodes where the declared outcome and the resulting account state disagreed.",
    },
    "forbidden_behavior": {
        "rule": "Never solicit a credential. If the caller offers one, refuse plainly, redirect to the official app, and continue.",
        "why": "Episodes where a guardrail fired.",
    },
    "required_communication": {
        "rule": "Say the disclosures this scenario requires before closing.",
        "why": "Episodes that omitted a mandatory disclosure.",
    },
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def mint(experiment: str = "v12-dynamic-full", scenario_dir: Path | None = None) -> dict[str, Any]:
    """Derive lessons from an experiment's confirmed failures."""
    scenario_dir = scenario_dir or (EMI / "dynamic_scenarios_v1")
    metrics = _read_jsonl(EXPERIMENTS / experiment / "metrics.jsonl")
    runs = {row["scenario_id"]: row for row in _read_jsonl(EXPERIMENTS / experiment / "runs.jsonl")}

    families: dict[str, list[str]] = defaultdict(list)
    scenario_family: dict[str, str] = {}
    for split in ("development", "validation", "regression"):
        for record in _read_jsonl(scenario_dir / f"{split}.jsonl"):
            scenario_family[record["scenario_id"]] = record.get("failure_family", "unknown")

    evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in metrics:
        failure = row.get("first_failure")
        if not failure or failure not in LESSON_TEMPLATES:
            continue
        # Only confirmed failures on valid simulations teach anything.
        if not row.get("valid_simulation"):
            continue
        scenario_id = row["scenario_id"]
        families[failure].append(scenario_id)
        localisation = row.get("failure_localization") or {}
        evidence[failure].append(
            {
                "scenario_id": scenario_id,
                "failure_family": scenario_family.get(scenario_id),
                "said": localisation.get("evidence"),
                "turn": localisation.get("turn_sequence"),
                "tools_called": [event["name"] for event in runs.get(scenario_id, {}).get("tool_events", [])],
            }
        )

    lessons = []
    for failure, scenario_ids in sorted(families.items()):
        template = LESSON_TEMPLATES[failure]
        lessons.append(
            {
                "lesson_id": f"L-{failure}",
                "triggered_by": failure,
                "applies_to_families": sorted({scenario_family.get(s, "unknown") for s in scenario_ids}),
                "rule": template["rule"],
                "why": template["why"],
                "confirmed_on": sorted(scenario_ids),
                "episode_count": len(scenario_ids),
                "evidence": evidence[failure][:3],
                "status": "candidate",
            }
        )

    payload = {
        "schema_version": "lesson-store.v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "source_experiment": experiment,
        "lessons": lessons,
        "lesson_count": len(lessons),
        "provenance": (
            "Every lesson is minted from failures the deterministic checker confirmed on valid simulations. "
            "No lesson originates from a language model's opinion."
        ),
        "governance": (
            "Lessons are candidates, not deployments. Injecting them produces a new agent candidate that must pass "
            "the same frozen evaluation and the same per-case release gate as any prompt change."
        ),
    }
    payload["content_hash"] = hashlib.sha256(
        json.dumps(payload["lessons"], sort_keys=True).encode("utf-8")
    ).hexdigest()
    write_json(OUTPUT, payload)
    return payload


def relevant_lessons(store: dict[str, Any], failure_family: str) -> list[dict[str, Any]]:
    """The lessons that apply to a scenario, so injection stays scoped.

    A lesson learned on callback scenarios should not be pasted into an
    unrelated one; broad injection is how prompts bloat and regress.
    """
    return [lesson for lesson in store.get("lessons", []) if failure_family in lesson.get("applies_to_families", [])]


def render_for_prompt(lessons: list[dict[str, Any]]) -> str:
    """Render scoped lessons as an instruction block appended to a candidate."""
    if not lessons:
        return ""
    lines = ["## Lessons from previous evaluated failures", ""]
    for lesson in lessons:
        lines.append(f"- {lesson['rule']}")
    return "\n".join(lines)


if __name__ == "__main__":
    result = mint()
    print(f"{result['lesson_count']} lessons minted from {result['source_experiment']} -> {OUTPUT}")
    for lesson in result["lessons"]:
        print(f"  {lesson['lesson_id']:28s} {lesson['episode_count']:2d} episodes  {lesson['applies_to_families']}")
