"""Export a redacted, frontend-ready monitoring snapshot."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from improvement.evaluate import ROOT, read_jsonl


DEFAULT_OUTPUT = ROOT.parent / "dashboard" / "public" / "dashboard-data.json"


def read_json(path: Path, fallback: Any = None) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def build_snapshot() -> dict[str, Any]:
    summary = read_json(ROOT / "artifacts" / "baseline" / "summary.json", {})
    scorecards = read_jsonl(ROOT / "artifacts" / "baseline" / "scorecards.jsonl")
    failures = read_json(ROOT / "artifacts" / "baseline" / "failure_clusters.json", {"clusters": []})
    lineage = read_json(ROOT / "artifacts" / "optimization" / "lineage.json", {})
    tracking = read_json(ROOT / "artifacts" / "experiments" / "mlflow_run.json", {})
    scenarios = read_jsonl(ROOT / "dataset" / "scenarios-v2.jsonl")
    split_counts: dict[str, int] = {}
    for item in scenarios:
        split = item["split"]
        split_counts[split] = split_counts.get(split, 0) + 1

    selected = next((item for item in lineage.get("candidate_scores", []) if item.get("is_selected")), {})
    baseline_policy = (lineage.get("candidate_scores") or [{}])[0].get("policy_score")
    calls = []
    for card in scorecards:
        human = card["human"]
        observed = card["observed"]
        calls.append({
            "runId": card["run_id"],
            "scenarioId": card["scenario_id"],
            "corpusRole": card["corpus_role"],
            "benchmarkMember": card["benchmark_member"],
            "primaryEligible": card["primary_eligible"],
            "language": observed["language"],
            "durationSeconds": observed["duration_seconds"],
            "averageAgentResponseSeconds": observed["average_agent_response_seconds"],
            "endedBy": observed["ended_by"],
            "actualDisposition": observed["actual_disposition"],
            "expectedDisposition": observed["expected_disposition"],
            "primarySuccess": human["primary_success"],
            "taskSuccess": human["task_success"],
            "failureCategory": human["failure_category"],
            "failureOwner": human["failure_owner"],
            "severity": human["severity"],
            "firstBreakingTurn": human["first_breaking_turn"],
            "note": human["note"],
            "integrityViolation": human["integrity_violation"],
            "hardSafetyViolation": human["hard_safety_violation"],
            "summaryIssues": observed["summary_issues"],
            "firstDirectAskTurn": observed["first_direct_ask_turn"],
            "explicitCommitmentTurn": observed["explicit_commitment_turn"],
            "redundantConfirmationTurns": observed["redundant_confirmation_turns"],
            "source": card["source"],
            "evaluationStatus": "frozen_baseline",
            "startDatetime": "",
            "trace": card["trace"],
        })

    evaluated_by_attempt = {item["source"]["attempt_id"]: item for item in calls}
    operational_path = ROOT / "artifacts" / "monitoring" / "calls.jsonl"
    operational_records = read_jsonl(operational_path) if operational_path.exists() else []
    operational_calls = []
    for record in operational_records:
        attempt = record["attempt"]
        attempt_id = record["source"]["attempt_id"]
        evaluated = evaluated_by_attempt.get(attempt_id)
        if evaluated:
            operational_calls.append({**evaluated, "startDatetime": attempt.get("start_datetime", "")})
            continue
        variables = attempt.get("agent_variables", {})
        operational_calls.append({
            "runId": record["run_id"],
            "scenarioId": "outside-frozen-selection",
            "corpusRole": "operational",
            "benchmarkMember": False,
            "primaryEligible": False,
            "language": attempt.get("language_name") or "Unknown",
            "durationSeconds": round(float(attempt.get("duration_in_seconds", 0) or 0), 2),
            "averageAgentResponseSeconds": attempt.get("average_agent_response_time_in_seconds"),
            "endedBy": attempt.get("ended_by") or "unknown",
            "actualDisposition": variables.get("disposition") or "unknown",
            "expectedDisposition": "not_evaluated",
            "primarySuccess": None,
            "taskSuccess": None,
            "failureCategory": "not_evaluated",
            "failureOwner": "not_evaluated",
            "severity": "none",
            "firstBreakingTurn": None,
            "note": "Operational trace outside the frozen 20-call evaluation selection.",
            "integrityViolation": False,
            "hardSafetyViolation": False,
            "summaryIssues": [],
            "firstDirectAskTurn": None,
            "explicitCommitmentTurn": None,
            "redundantConfirmationTurns": [],
            "source": {**record["source"], "app_version": 0},
            "evaluationStatus": "not_evaluated",
            "startDatetime": attempt.get("start_datetime", ""),
            "trace": [{**message, "flags": []} for message in record.get("messages", [])],
        })

    return {
        "schemaVersion": "loopline-dashboard.v1",
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "mode": "frozen-baseline",
        "summary": summary,
        "calls": calls,
        "operationalCalls": operational_calls or calls,
        "monitoring": {
            "recentAttempts": len(operational_calls or calls),
            "evaluatedAttempts": sum(item["evaluationStatus"] == "frozen_baseline" for item in (operational_calls or calls)),
            "unscoredAttempts": sum(item["evaluationStatus"] == "not_evaluated" for item in (operational_calls or calls)),
            "benchmarkRemainsFrozen": True,
        },
        "failureClusters": failures.get("clusters", []),
        "experiment": {
            "mlflow": tracking,
            "optimizer": lineage.get("optimizer"),
            "claimBoundary": lineage.get("claim_boundary"),
            "candidateCount": lineage.get("candidate_count"),
            "selectedIndex": lineage.get("selected_index"),
            "selectedSha256": lineage.get("selected_sha256"),
            "baselinePolicyScore": baseline_policy,
            "candidatePolicyScore": selected.get("policy_score"),
            "candidateVersion": "historical-static-precheck",
            "candidateCases": selected.get("cases", []),
        },
        "evaluationSet": {
            "totalContracts": len(scenarios),
            "splitCounts": split_counts,
            "provenance": "tau2-inspired stateful contracts with MatrAIx-inspired behavior fields; synthetic and not benchmark evidence",
        },
        "pipeline": [
            {"id": "ingest", "label": "Ingest + redact", "status": "complete", "detail": "20 Indus calls frozen"},
            {"id": "evaluate", "label": "Trace evaluation", "status": "complete", "detail": "20/20 provisionally labelled; owner review pending"},
            {"id": "mine", "label": "Failure mining", "status": "complete", "detail": f"{len(failures.get('clusters', []))} ranked clusters"},
            {"id": "optimize", "label": "Repair experiments", "status": "complete", "detail": "See Framework view for V3 evidence"},
            {"id": "gate", "label": "Pre-held-out gate", "status": "complete", "detail": "GEPA derivative selected for owner review"},
            {"id": "voice", "label": "Matched voice round", "status": "waiting", "detail": "After owner review, held-out, and Indus commit"},
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    snapshot = build_snapshot()
    existing = read_json(args.output, {})
    if isinstance(existing, dict) and "framework" in existing:
        snapshot["framework"] = existing["framework"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(snapshot['calls'])} calls to {args.output}")


if __name__ == "__main__":
    main()
