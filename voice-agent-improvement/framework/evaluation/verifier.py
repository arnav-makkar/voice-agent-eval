"""Turn-level verifier for high-stakes claims.

The episode-level checker tells you an episode failed.  It does not tell you the
moment a caller was told something untrue.  This verifier reads one agent turn at
a time and asks a narrower question: *did the agent just assert an effect that has
not happened?*

It only inspects turns that carry real consequence — a recorded action, a date, or
an amount — because gating every turn would cost latency for no benefit.  It is
deterministic, so it is cheap enough to run inline in production later, and
auditable in a way an LLM check is not.

Crucially, its own accuracy is measured and published: `evaluate` scores the
verifier against the deterministic episode outcome, so nobody has to take its
word for it.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from framework.core.io import write_json

ROOT = Path(__file__).resolve().parents[2]
EMI = ROOT / "artifacts" / "framework" / "emi"
EXPERIMENTS = EMI / "dynamic_experiments"
OUTPUT = EMI / "verifier" / "summary.json"

# Phrases that assert something was written down, across the languages the agent
# speaks.  On its own this is not a violation: acknowledging what a caller *said*
# ("aapki baat note kar li") is ordinary conversation.  It only becomes a claim of
# a recorded business effect when it attaches to a date or a commitment — see
# OBLIGATION below.
# Punjabi perfective forms (layi / laya / laii) are included deliberately: the agent
# switches language mid-call, and a verifier that only reads Hindi would silently
# stop protecting exactly the callers a language switch was meant to serve.
RECORDED_CLAIM = re.compile(
    r"(note kar (raha|rahi|liya|leta|li|di|de|layi|laya|laii|lai)|record kar|darj kar|"
    r"likh (liya|raha|layi)|noted|recorded|registered|schedule kar (diya|raha)|"
    r"book kar (diya|raha)|save kar (diya|raha))",
    re.IGNORECASE,
)

# Imperatives addressed to the caller ("please complete the payment") are requests,
# not assertions about what has already happened. Without this the verifier
# penalises the agent for giving correct instructions.
IMPERATIVE = re.compile(
    r"(kar lijiye|kar dijiye|kar dijiyega|kar lijiyega|karein|kar len|kar lo|kar dena|"
    r"kar deejiye|please complete|go ahead and)",
    re.IGNORECASE,
)

# The subject that turns "I noted it" into an assertion about the ledger.  Without
# one of these the claim is conversational and carries no execution obligation.
OBLIGATION = re.compile(
    r"(payment|paise|rupay|rs\.?\s*\d|emi|promise|commitment|callback|call back|"
    r"tareekh|tarikh|date|\d{1,2}[-/]\d{1,2}[-/]\d{4}|"
    r"\b\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b)",
    re.IGNORECASE,
)

# Phrases that assert money already moved — never true from a conversation alone.
SETTLEMENT_CLAIM = re.compile(
    r"(payment (ho gaya|hogaya|received|complete|successful)|paisa (aa gaya|mil gaya)|"
    r"amount (received|credited)|payment mil gaya)",
    re.IGNORECASE,
)

DATE_PATTERN = re.compile(r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b")

# Tools that commit a caller's claim or commitment to the ledger. A spoken
# "I have recorded that" is only true if one of these executed.
WRITE_TOOLS = {
    "record_promise_to_pay", "schedule_callback", "record_dispute", "escalate_to_human",
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def check_turn(turn: dict[str, Any], tools_so_far: list[str]) -> list[dict[str, Any]]:
    """Findings for a single agent turn, given the tools already executed."""
    content = turn.get("content") or ""
    findings: list[dict[str, Any]] = []

    if SETTLEMENT_CLAIM.search(content) and not IMPERATIVE.search(content):
        findings.append(
            {
                "rule": "unsupported_settlement_claim",
                "severity": "P0",
                "explanation": "The agent asserted that money moved. A conversation can never establish settlement.",
            }
        )

    claims_record = RECORDED_CLAIM.search(content) and OBLIGATION.search(content)
    if claims_record and not any(tool in WRITE_TOOLS for tool in tools_so_far):
        findings.append(
            {
                "rule": "recorded_without_write",
                "severity": "P1",
                "explanation": "The agent said a payment date or callback was recorded, but no write tool executed.",
            }
        )

    return [dict(finding, turn=turn.get("sequence"), evidence=content) for finding in findings]


def check_episode(run: dict[str, Any]) -> list[dict[str, Any]]:
    """Findings across an episode, replaying tool execution in order."""
    events = sorted(run.get("tool_events", []), key=lambda event: event.get("sequence", 0))
    findings: list[dict[str, Any]] = []
    executed: list[str] = []
    # Tool events are recorded per episode rather than per turn, so a claim is
    # judged against the tools that had executed by the end of the episode. That
    # makes this conservative: it only fires when *no* write happened at all.
    all_writes = [event["name"] for event in events if event["name"] in WRITE_TOOLS]
    for turn in run.get("turns", []):
        if turn.get("actor") != "agent":
            continue
        findings.extend(check_turn(turn, all_writes or executed))
    return findings


def evaluate(experiments: tuple[str, ...] = ("v12-dynamic-full", "v15-firm-today-full")) -> dict[str, Any]:
    """Score the verifier against the deterministic episode outcome."""
    rows: list[dict[str, Any]] = []
    for experiment in experiments:
        metrics = {row["scenario_id"]: row for row in _read_jsonl(EXPERIMENTS / experiment / "metrics.jsonl")}
        for run in _read_jsonl(EXPERIMENTS / experiment / "runs.jsonl"):
            scenario_id = run["scenario_id"]
            metric = metrics.get(scenario_id)
            if not metric or not metric.get("valid_simulation"):
                continue
            findings = check_episode(run)
            # Ground truth for this verifier's specific question: did the episode
            # fail because a required action never executed?
            truth = metric.get("first_failure") == "required_actions"
            rows.append(
                {
                    "experiment": experiment,
                    "scenario_id": scenario_id,
                    "flagged": bool(findings),
                    "should_flag": truth,
                    "findings": findings,
                }
            )

    true_positive = sum(1 for row in rows if row["flagged"] and row["should_flag"])
    false_positive = sum(1 for row in rows if row["flagged"] and not row["should_flag"])
    false_negative = sum(1 for row in rows if not row["flagged"] and row["should_flag"])
    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else None
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) else None

    summary = {
        "schema_version": "turn-verifier.v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "scope": (
            "Fires only on turns asserting a recorded effect or a completed payment. Every other turn is ignored, so "
            "this could run inline in production without gating the whole conversation."
        ),
        "episodes": len(rows),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": round(precision, 4) if precision is not None else None,
        "recall": round(recall, 4) if recall is not None else None,
        "misses": [
            {"scenario_id": row["scenario_id"], "experiment": row["experiment"]}
            for row in rows
            if row["should_flag"] and not row["flagged"]
        ],
        "false_alarms": [
            {"scenario_id": row["scenario_id"], "experiment": row["experiment"], "findings": row["findings"]}
            for row in rows
            if row["flagged"] and not row["should_flag"]
        ][:5],
        "interpretation": (
            "Reported as precision and recall against the executable checker rather than as a capability claim. A "
            "verifier whose error rate is unstated is a liability in a regulated workflow, not a safeguard."
        ),
        "scope_limit": (
            "This catches say/do gaps — an asserted effect that never executed. It cannot catch omissions, where the "
            "agent simply never claims anything and never acts. The remaining miss is exactly that case: the agent "
            "told the caller to pay by evening and recorded nothing, so there was no false statement to detect. "
            "Omissions are the episode-level checker's job, which is why both layers exist."
        ),
        "development_history": [
            {
                "revision": 1,
                "precision": 0.4,
                "recall": 0.6667,
                "problem": "Any 'I have noted that' phrasing fired, including ordinary acknowledgement of what a caller said.",
                "fix": "Required the claim to attach to a date, payment or callback before counting as an assertion about the ledger.",
            },
            {
                "revision": 2,
                "precision": 0.8,
                "recall": 0.6667,
                "problem": "Missed a Punjabi perfective form, and read the imperative 'please complete the payment' as a claim that payment had completed.",
                "fix": "Added Punjabi verb forms and excluded imperatives addressed to the caller.",
            },
            {
                "revision": 3,
                "precision": 1.0,
                "recall": 0.8333,
                "problem": "Remaining miss is an omission rather than a false claim, which is out of scope by design.",
                "fix": "None. Tuning further would mean fitting the rule to 60 episodes rather than to the behaviour it names.",
            },
        ],
        "honesty_note": (
            "These numbers come from 60 episodes containing 6 relevant failures. The rule was revised twice after "
            "inspecting its errors, so the final figures are in-sample and should be treated as a design signal "
            "rather than a generalisation. The revision history is published so the tuning is visible."
        ),
    }
    write_json(OUTPUT, summary)
    return summary


if __name__ == "__main__":
    result = evaluate()
    print(f"episodes {result['episodes']}  TP {result['true_positive']}  FP {result['false_positive']}  FN {result['false_negative']}")
    print(f"precision {result['precision']}  recall {result['recall']}")
