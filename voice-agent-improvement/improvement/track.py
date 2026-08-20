"""Log the frozen baseline and prompt-search lineage to a local MLflow store."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import mlflow

from improvement.evaluate import ROOT


DEFAULT_TRACKING_DB = ROOT / "artifacts" / "experiments" / "mlflow.db"
DEFAULT_RECORD = ROOT / "artifacts" / "experiments" / "mlflow_run.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tracking-db", type=Path, default=DEFAULT_TRACKING_DB)
    parser.add_argument("--record", type=Path, default=DEFAULT_RECORD)
    args = parser.parse_args()

    summary_path = ROOT / "artifacts" / "baseline" / "summary.json"
    clusters_path = ROOT / "artifacts" / "baseline" / "failure_clusters.json"
    scorecards_path = ROOT / "artifacts" / "baseline" / "scorecards.jsonl"
    lineage_path = ROOT / "artifacts" / "optimization" / "lineage.json"
    candidate_path = ROOT / "agent" / "candidates" / "gepa-v13" / "SYSTEM-PROMPT.md"
    summary = read_json(summary_path)
    lineage = read_json(lineage_path)
    selected = next(item for item in lineage["candidate_scores"] if item["is_selected"])
    baseline_candidate = lineage["candidate_scores"][0]

    args.tracking_db.parent.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(f"sqlite:///{args.tracking_db.resolve()}")
    mlflow.set_experiment("easycredit-voice-agent-improvement")
    with mlflow.start_run(run_name="indus-v12-baseline-to-gepa-v13") as run:
        mlflow.log_params({
            "baseline_version": summary["baseline_version"],
            "candidate_version": "gepa-v13",
            "optimizer": lineage["optimizer"],
            "voice_baseline_calls": summary["corpus_calls"],
            "matched_benchmark_calls": summary["benchmark_calls"],
            "candidate_count": lineage["candidate_count"],
            "claim_boundary": lineage["claim_boundary"],
        })
        mlflow.log_metrics({
            "baseline_primary_tsr": summary["tsr"],
            "baseline_task_success": summary["task_success_rate"],
            "baseline_disposition_accuracy": summary["disposition_accuracy"],
            "baseline_integrity_violation_rate": summary["integrity_violation_rate"],
            "baseline_redundant_confirmation_rate": summary["redundant_confirmation_rate"],
            "baseline_policy_contract_score": baseline_candidate["policy_score"],
            "candidate_policy_contract_score": selected["policy_score"],
        })
        mlflow.set_tags({
            "release_gate": summary["release_gate"]["status"],
            "evidence": "20 real self-recorded Sarvam Indus calls",
            "optimizer_result": "offline-policy-candidate-only",
            "voice_tsr_claim": "requires-matched-candidate-round",
        })
        for artifact in (summary_path, clusters_path, scorecards_path, lineage_path, candidate_path):
            mlflow.log_artifact(str(artifact), artifact_path="evidence")
        record = {
            "schema_version": "mlflow-lineage.v1",
            "experiment_name": "easycredit-voice-agent-improvement",
            "run_id": run.info.run_id,
            "tracking_uri": mlflow.get_tracking_uri(),
            "run_name": "indus-v12-baseline-to-gepa-v13",
            "claim_boundary": lineage["claim_boundary"],
        }

    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
