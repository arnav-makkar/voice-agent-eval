"""Aggregate turn-level annotations into an evidence-ranked improvement backlog."""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
from typing import Any

from improvement.evaluate import ROOT, SEVERITY_WEIGHT, read_jsonl


DEFAULT_SCORECARDS = ROOT / "artifacts" / "baseline" / "scorecards.jsonl"
DEFAULT_OUTPUT = ROOT / "artifacts" / "baseline" / "failure_clusters.json"

RECOMMENDATIONS = {
    "redundant_confirmation": "Treat an explicit pay-now commitment as terminal: acknowledge once and end without another question.",
    "dispute_misclassified_wrong_number": "Give dispute precedence when the named customer denies the purchase; wrong_number applies only when the person is not the named customer.",
    "channel_unavailable_loop": "After one app-unavailable statement, stop repeating download instructions and offer one realistic date or callback path.",
    "late_charge_misstatement": "Say the frozen outstanding already includes the stated late charge; never say it may apply later.",
    "unsupported_future_completion_claim": "Record a promise as a promise; never state that payment will be done or has completed.",
    "repeated_pressure_after_channel_refusal": "If the caller refuses to continue with an AI twice, provide the official human-support route and end recovery pressure.",
    "trust_resolution_missing_direct_close": "Resolve authenticity in one turn: identify AI status, give independent official-app verification, then ask one pay-now question.",
    "conditional_check_not_converted": "After a conditional app-check response, use one concise verify-then-pay micro-close and stop if commitment remains absent.",
    "caller_disengagement_after_interruption": "After interruption, restate only lender, product, amount and one action before asking again.",
    "invalid_output_disposition": "Fix the output extractor taxonomy separately; the agent prompt cannot repair an invalid enum value reliably.",
}


def mine(scorecards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for card in scorecards:
        category = card["human"]["failure_category"]
        if category != "none":
            grouped[category].append(card)
    clusters = []
    for category, cards in grouped.items():
        prompt_fixable = any(card["human"]["prompt_fixable"] for card in cards)
        max_severity = max(cards, key=lambda card: SEVERITY_WEIGHT[card["human"]["severity"]])["human"]["severity"]
        business_impact = sum(
            3 if card["primary_eligible"] and not card["human"]["primary_success"] else 1
            for card in cards
        )
        priority_score = len(cards) * SEVERITY_WEIGHT[max_severity] * business_impact
        clusters.append({
            "cluster_id": category,
            "count": len(cards),
            "max_severity": max_severity,
            "business_impact": business_impact,
            "priority_score": priority_score,
            "prompt_fixable": prompt_fixable,
            "recommendation": RECOMMENDATIONS.get(category, "Review the source traces."),
            "evidence": [
                {
                    "run_id": card["run_id"],
                    "turn_id": card["human"]["first_breaking_turn"],
                    "note": card["human"]["note"],
                }
                for card in cards
            ],
        })
    return sorted(clusters, key=lambda item: (item["prompt_fixable"], item["priority_score"]), reverse=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scorecards", type=Path, default=DEFAULT_SCORECARDS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    clusters = mine(read_jsonl(args.scorecards))
    payload = {"schema_version": "failure-clusters.v1", "clusters": clusters}
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
