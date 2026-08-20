"""MLflow tracking adapter; experiment artifacts remain useful if MLflow is absent."""

from __future__ import annotations

from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
TRACKING_DB = ROOT / "artifacts" / "experiments" / "mlflow.db"


def log_experiment(metadata: dict[str, Any], artifact_dir: Path) -> dict[str, Any]:
    try:
        import mlflow
    except ImportError:
        return {"status": "unavailable", "reason": "mlflow optional dependency is not installed"}

    mlflow.set_tracking_uri(f"sqlite:///{TRACKING_DB}")
    mlflow.set_experiment("self-improving-voice-agent-framework")
    with mlflow.start_run(run_name=metadata["experiment_id"]) as run:
        mlflow.set_tags(
            {
                "framework.schema": metadata["schema_version"],
                "candidate.id": metadata["candidate_id"],
                "dataset.id": metadata["dataset_id"],
                "evaluator.version": metadata["evaluator_version"],
                "judge.model": metadata["judge_model"],
                "agent.model": metadata.get("agent_model", "unknown"),
            }
        )
        mlflow.log_params(
            {
                "candidate_prompt_sha256": metadata["candidate_prompt_sha256"],
                "splits": ",".join(metadata["splits"]),
                "cases": metadata["summary"]["cases"],
            }
        )
        for name, value in metadata["summary"].items():
            if isinstance(value, (int, float)):
                mlflow.log_metric(name, float(value))
        for path in artifact_dir.iterdir():
            if path.is_file():
                mlflow.log_artifact(str(path))
        return {"status": "logged", "run_id": run.info.run_id, "experiment_id": run.info.experiment_id, "tracking_uri": f"sqlite:///{TRACKING_DB}"}


def log_optimizer(metadata: dict[str, Any], artifact_dir: Path) -> dict[str, Any]:
    """Log a search run without pretending it is a matched candidate evaluation."""
    try:
        import mlflow
    except ImportError:
        return {"status": "unavailable", "reason": "mlflow optional dependency is not installed"}

    mlflow.set_tracking_uri(f"sqlite:///{TRACKING_DB}")
    mlflow.set_experiment("self-improving-voice-agent-framework")
    run_name = f"gepa-{metadata['dataset_id']}-{metadata['seed_sha256'][:8]}"
    with mlflow.start_run(run_name=run_name) as run:
        mlflow.set_tags(
            {
                "framework.schema": metadata["schema_version"],
                "run.kind": "optimizer_search",
                "optimizer": metadata["optimizer"],
                "dataset.id": metadata["dataset_id"],
                "heldout.accessed": str(metadata["held_out_accessed"]).lower(),
                "reflection.model": metadata["reflection_model"],
                "agent.model": metadata["agent_model"],
            }
        )
        mlflow.log_params(
            {
                "seed_sha256": metadata["seed_sha256"],
                "dataset_manifest_sha256": metadata["dataset_manifest_sha256"],
                "max_metric_calls": metadata["max_metric_calls"],
                "max_candidate_proposals": metadata["max_candidate_proposals"],
                "acceptance_criterion": metadata["acceptance_criterion"],
            }
        )
        mlflow.log_metric("engine_candidate_count", float(metadata["engine_candidate_count"]))
        mlflow.log_metric("recorded_evaluations", float(len(metadata["evaluations"])))
        mlflow.log_metric("reflections", float(len(metadata["reflections"])))
        for path in artifact_dir.iterdir():
            if path.is_file():
                mlflow.log_artifact(str(path))
        return {"status": "logged", "run_id": run.info.run_id, "experiment_id": run.info.experiment_id, "tracking_uri": f"sqlite:///{TRACKING_DB}"}


def log_dynamic_evaluation(metadata: dict[str, Any], artifact_dir: Path) -> dict[str, Any]:
    """Log one complete stateful candidate suite with explicit evidence type."""
    try:
        import mlflow
    except ImportError:
        return {"status": "unavailable", "reason": "mlflow optional dependency is not installed"}
    mlflow.set_tracking_uri(f"sqlite:///{TRACKING_DB}")
    mlflow.set_experiment("self-improving-voice-agent-framework")
    with mlflow.start_run(run_name=metadata["experiment_id"]) as run:
        mlflow.set_tags(
            {
                "run.kind": "stateful_dynamic_evaluation",
                "candidate.id": metadata["candidate_id"],
                "dataset.id": metadata["dataset_id"],
                "adapter": metadata["adapter"],
                "evidence.mode": "text_proxy",
            }
        )
        mlflow.log_params(
            {
                "candidate_prompt_sha256": metadata["prompt_sha256"],
                "splits": ",".join(metadata["splits"]),
                "scenarios": metadata["scenario_count"],
                "model": metadata["model"],
            }
        )
        for name, value in metadata["aggregate"].items():
            if isinstance(value, (int, float)):
                mlflow.log_metric(name, float(value))
        for path in artifact_dir.iterdir():
            if path.is_file():
                mlflow.log_artifact(str(path))
        return {
            "status": "logged",
            "run_id": run.info.run_id,
            "experiment_id": run.info.experiment_id,
            "tracking_uri": f"sqlite:///{TRACKING_DB}",
        }
