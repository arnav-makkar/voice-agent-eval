"""Score voice traces and locate the first observable breaking turn."""

from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CALLS = ROOT / "artifacts" / "baseline" / "calls.jsonl"
DEFAULT_ANNOTATIONS = Path(__file__).with_name("human_annotations.json")
DEFAULT_SCORECARDS = ROOT / "artifacts" / "baseline" / "scorecards.jsonl"
DEFAULT_SUMMARY = ROOT / "artifacts" / "baseline" / "summary.json"

PAYMENT_WORDS = ("payment", "pay", "पे", "भुगतान")
NOW_WORDS = ("अभी", "now", "right away", "ਹੁਣ", "hun")
COMMITMENT_PATTERNS = (
    r"कर (?:देता|दूंगा|दूं|रहा)",
    r"करता (?:हूँ|हूं)",
    r"pay करता",
    r"payment कर",
    r"i(?:'ll| will) (?:do|pay|make)",
    r"do that now",
    r"payment ਕਰਦ",
)
SUMMARY_ISSUES = {
    "samuel": "product hallucination: Samuel",
    "overdose": "semantic hallucination: overdose",
    "overdues": "grammar corruption: overdues",
    "immediatey": "spelling corruption: immediatey",
    "emipayment": "word-boundary corruption: EMIpayment",
    "let charges": "entity corruption: let charges",
}
SEVERITY_WEIGHT = {"P0": 8, "P1": 4, "P2": 2, "P3": 1, "none": 0}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def has_payment_language(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in PAYMENT_WORDS)


def is_direct_ask(text: str) -> bool:
    lowered = text.lower()
    return (
        has_payment_language(lowered)
        and any(word in lowered for word in NOW_WORDS)
        and ("?" in text or "क्या" in text or "can you" in lowered or "will you" in lowered)
    )


def is_explicit_commitment(text: str, previous_agent_text: str = "") -> bool:
    lowered = text.lower()
    if any(term in lowered for term in ("नहीं", "नही", "never", "don't", "do not", "not pay", "duplicate")):
        return False
    if any(term in lowered for term in ("check", "देखता", "देखूंगा", "later", "बाद में")) and not has_payment_language(lowered):
        return False
    pattern_hit = any(re.search(pattern, lowered) for pattern in COMMITMENT_PATTERNS)
    payment_context = has_payment_language(lowered) or (
        has_payment_language(previous_agent_text) and any(word in lowered for word in NOW_WORDS)
    )
    return bool(pattern_hit and payment_context)


def score_call(call: dict[str, Any], annotation: dict[str, Any]) -> dict[str, Any]:
    messages = call["messages"]
    first_direct_ask_turn = None
    commitment_turn = None
    previous_agent = ""
    for message in messages:
        text = str(message.get("content", ""))
        if message.get("role") == "assistant":
            previous_agent = text
            if first_direct_ask_turn is None and is_direct_ask(text):
                first_direct_ask_turn = message.get("turn_id")
        elif commitment_turn is None and is_explicit_commitment(text, previous_agent):
            commitment_turn = message.get("turn_id")

    repeated_confirmation_turns: list[int] = []
    if commitment_turn is not None:
        for message in messages:
            turn_id = int(message.get("turn_id", 0))
            if (
                turn_id > commitment_turn
                and message.get("role") == "assistant"
                and is_direct_ask(str(message.get("content", "")))
            ):
                repeated_confirmation_turns.append(turn_id)

    attempt = call["attempt"]
    variables = attempt.get("agent_variables", {})
    actual_disposition = variables.get("disposition")
    expected_disposition = call["expected_disposition"]
    summary_text = str(variables.get("callSummary", ""))
    summary_issues = [label for token, label in SUMMARY_ISSUES.items() if token in summary_text.lower()]
    automated_primary_success = commitment_turn is not None
    automated_task_success = (
        automated_primary_success
        if expected_disposition == "payment_ready"
        else actual_disposition == expected_disposition
    )

    trace = []
    for message in messages:
        turn_id = int(message.get("turn_id", 0))
        flags = []
        if turn_id == first_direct_ask_turn:
            flags.append("first_direct_ask")
        if turn_id == commitment_turn:
            flags.append("explicit_commitment")
        if turn_id in repeated_confirmation_turns:
            flags.append("redundant_confirmation")
        if turn_id == annotation.get("first_breaking_turn"):
            flags.append("first_breaking_turn")
        trace.append({**message, "flags": flags})

    agent_messages = [m for m in messages if m.get("role") == "assistant"]
    word_counts = [len(str(m.get("content", "")).split()) for m in agent_messages]
    return {
        "schema_version": "voice-scorecard.v1",
        "run_id": call["run_id"],
        "scenario_id": call["scenario_id"],
        "corpus_role": call["corpus_role"],
        "benchmark_member": call["benchmark_member"],
        "primary_eligible": call["primary_eligible"],
        "source": call["source"],
        "observed": {
            "language": attempt.get("language_name"),
            "duration_seconds": round(float(attempt.get("duration_in_seconds", 0)), 2),
            "message_count": attempt.get("num_messages"),
            "average_agent_response_seconds": attempt.get("average_agent_response_time_in_seconds"),
            "ended_by": attempt.get("ended_by"),
            "actual_disposition": actual_disposition,
            "expected_disposition": expected_disposition,
            "first_direct_ask_turn": first_direct_ask_turn,
            "explicit_commitment_turn": commitment_turn,
            "redundant_confirmation_turns": repeated_confirmation_turns,
            "average_agent_words": round(sum(word_counts) / max(len(word_counts), 1), 1),
            "summary_issues": summary_issues,
        },
        "automated": {
            "primary_success": automated_primary_success,
            "task_success": automated_task_success,
        },
        "human": annotation,
        "evaluator_agreement": {
            "primary_success": automated_primary_success == annotation["primary_success"],
            "task_success": automated_task_success == annotation["task_success"],
        },
        "trace": trace,
    }


def summarize(scorecards: list[dict[str, Any]]) -> dict[str, Any]:
    benchmark = [item for item in scorecards if item["benchmark_member"]]
    eligible = [item for item in benchmark if item["primary_eligible"]]
    all_primary_eligible = [item for item in scorecards if item["primary_eligible"]]
    clusters = collections.Counter(
        item["human"]["failure_category"]
        for item in scorecards
        if item["human"]["failure_category"] != "none"
    )
    prompt_clusters = collections.Counter(
        item["human"]["failure_category"]
        for item in scorecards
        if item["human"]["prompt_fixable"] and item["human"]["failure_category"] != "none"
    )
    duration_values = [item["observed"]["duration_seconds"] for item in scorecards]
    summary = {
        "schema_version": "voice-baseline-summary.v1",
        "baseline_version": "indus-v12",
        "corpus_calls": len(scorecards),
        "benchmark_calls": len(benchmark),
        "exploratory_calls": len(scorecards) - len(benchmark),
        "primary_eligible_calls": len(eligible),
        "primary_successes": sum(item["human"]["primary_success"] for item in eligible),
        "tsr": round(sum(item["human"]["primary_success"] for item in eligible) / max(len(eligible), 1), 4),
        "all_corpus_eligible_calls": len(all_primary_eligible),
        "all_corpus_tsr": round(sum(item["human"]["primary_success"] for item in all_primary_eligible) / max(len(all_primary_eligible), 1), 4),
        "task_success_rate": round(sum(item["human"]["task_success"] for item in benchmark) / max(len(benchmark), 1), 4),
        "disposition_accuracy": round(sum(item["observed"]["actual_disposition"] == item["observed"]["expected_disposition"] for item in benchmark) / max(len(benchmark), 1), 4),
        "hard_safety_violation_rate": round(sum(item["human"]["hard_safety_violation"] for item in benchmark) / max(len(benchmark), 1), 4),
        "integrity_violation_rate": round(sum(item["human"]["integrity_violation"] for item in benchmark) / max(len(benchmark), 1), 4),
        "redundant_confirmation_rate": round(sum(bool(item["observed"]["redundant_confirmation_turns"]) for item in benchmark) / max(len(benchmark), 1), 4),
        "summary_issue_rate": round(sum(bool(item["observed"]["summary_issues"]) for item in scorecards) / max(len(scorecards), 1), 4),
        "average_duration_seconds": round(sum(duration_values) / max(len(duration_values), 1), 2),
        "evaluator_primary_agreement": round(sum(item["evaluator_agreement"]["primary_success"] for item in scorecards) / max(len(scorecards), 1), 4),
        "evaluator_task_agreement": round(sum(item["evaluator_agreement"]["task_success"] for item in scorecards) / max(len(scorecards), 1), 4),
        "failure_clusters": dict(clusters.most_common()),
        "prompt_fixable_clusters": dict(prompt_clusters.most_common()),
    }
    summary["release_gate"] = {
        "status": "fail" if any((summary["hard_safety_violation_rate"] > 0, summary["integrity_violation_rate"] > 0, summary["task_success_rate"] < 0.95)) else "pass",
        "reasons": [
            reason
            for condition, reason in (
                (summary["hard_safety_violation_rate"] > 0, "hard safety violation detected"),
                (summary["integrity_violation_rate"] > 0, "unsupported completion or platform-action claim detected"),
                (summary["task_success_rate"] < 0.95, "task success below 95% gate"),
                (summary["disposition_accuracy"] < 0.95, "disposition accuracy below 95% gate"),
            )
            if condition
        ],
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calls", type=Path, default=DEFAULT_CALLS)
    parser.add_argument("--annotations", type=Path, default=DEFAULT_ANNOTATIONS)
    parser.add_argument("--scorecards", type=Path, default=DEFAULT_SCORECARDS)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()

    calls = read_jsonl(args.calls)
    annotations = json.loads(args.annotations.read_text(encoding="utf-8"))
    by_run = {item["run_id"]: item for item in annotations}
    if set(by_run) != {item["run_id"] for item in calls}:
        raise SystemExit("annotation run IDs do not exactly match the frozen corpus")
    scorecards = [score_call(call, by_run[call["run_id"]]) for call in calls]
    summary = summarize(scorecards)
    args.scorecards.parent.mkdir(parents=True, exist_ok=True)
    with args.scorecards.open("w", encoding="utf-8") as handle:
        for item in scorecards:
            handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
