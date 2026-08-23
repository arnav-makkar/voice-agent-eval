"""Run GEPA Optimize Anything against complete stateful scenario episodes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import gepa.optimize_anything as oa
from gepa.optimize_anything import EngineConfig, GEPAConfig, ReflectionConfig, TrackingConfig

from framework.adapters.gemini import GeminiJsonClient, load_env_file
from framework.core.io import write_json, write_text
from framework.evaluation.candidates import GeminiPromptAgent
from framework.evaluation.contracts import EvaluationScenario
from framework.evaluation.metrics import evaluate_run
from framework.evaluation.runner import load_scenarios, run_scenario
from framework.experiments.run_gepa import GeminiEvidenceProposer, lint_deployable_candidate
from framework.experiments.tracking import log_optimizer


ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ROOT / "artifacts" / "framework" / "emi" / "dynamic_scenarios_v1"
DEFAULT_SEED = ROOT / "agent" / "candidates" / "v14-terminal-discipline.md"
OUTPUT = ROOT / "artifacts" / "framework" / "emi" / "dynamic_gepa"


def run(seed_path: Path, max_metric_calls: int, max_proposals: int) -> dict[str, Any]:
    load_env_file(ROOT / ".env")
    seed = seed_path.read_text(encoding="utf-8")
    development = load_scenarios(SCENARIOS / "development.jsonl")[:12]
    validation = load_scenarios(SCENARIOS / "validation.jsonl")
    agent_client = GeminiJsonClient(model="gemini-3.6-flash", cache_dir=ROOT / "artifacts" / "framework" / "cache")
    reflection_client = GeminiJsonClient(model="gemini-pro-latest", cache_dir=ROOT / "artifacts" / "framework" / "cache")
    proposer = GeminiEvidenceProposer(reflection_client)
    evaluations: list[dict[str, Any]] = []

    def evaluate(candidate: dict[str, str], example: dict[str, Any]):
        prompt = candidate["prompt"]
        scenario = EvaluationScenario.from_record(example)
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        candidate_id = "dynamic-gepa-" + prompt_hash[:12]
        compatibility = lint_deployable_candidate(prompt)
        if compatibility:
            side_info = {
                "scenario_id": scenario.scenario_id,
                "score": 0.0,
                "platform_compatibility_issues": compatibility,
                "actionable_instruction": "Repair deployability before behavioral scoring.",
            }
            evaluations.append({"candidate_id": candidate_id, "scenario_id": scenario.scenario_id, "score": 0.0, "side_info": side_info})
            oa.log(json.dumps(side_info, ensure_ascii=False))
            return 0.0, side_info
        agent = GeminiPromptAgent(candidate_id, prompt, agent_client)
        episode = run_scenario(agent, scenario, prompt_hash)
        metrics = evaluate_run(scenario, episode)
        severe = (
            not metrics["valid_simulation"]
            or not metrics["accuracy"]["forbidden_behavior"]
            or not metrics["accuracy"]["environment_state"]
            or not metrics["accuracy"]["required_actions"]
        )
        score = 0.0 if severe else round(0.75 * float(metrics["task_success"]) + 0.25 * metrics["experience"]["score"], 4)
        side_info = {
            "scenario_id": scenario.scenario_id,
            "failure_family": scenario.failure_family,
            "score": score,
            "metrics": metrics,
            "terminal_disposition": episode.agent_declared_disposition,
            "final_state": episode.final_state,
            "last_agent_turn": next((turn.content for turn in reversed(episode.turns) if turn.actor == "agent"), None),
            "actionable_instruction": "Fix the localized component without changing unrelated passing behavior.",
        }
        evaluations.append({"candidate_id": candidate_id, "scenario_id": scenario.scenario_id, "score": score, "side_info": side_info})
        oa.log(json.dumps(side_info, ensure_ascii=False))
        return score, side_info

    run_dir = OUTPUT / "engine"
    run_dir.mkdir(parents=True, exist_ok=True)
    config = GEPAConfig(
        engine=EngineConfig(
            run_dir=str(run_dir),
            seed=23,
            display_progress_bar=False,
            max_metric_calls=max_metric_calls,
            max_candidate_proposals=max_proposals,
            parallel=False,
            cache_evaluation=True,
            candidate_selection_strategy="pareto",
            acceptance_criterion="strict_improvement",
        ),
        reflection=ReflectionConfig(
            reflection_lm=None,
            custom_candidate_proposer=proposer,
            reflection_minibatch_size=3,
            skip_perfect_score=True,
            perfect_score=1.0,
        ),
        tracking=TrackingConfig(
            use_mlflow=True,
            mlflow_tracking_uri=f"sqlite:///{(ROOT / 'artifacts' / 'experiments' / 'mlflow.db').resolve()}",
            mlflow_experiment_name="the framework Dynamic GEPA",
            key_prefix="dynamic_gepa",
        ),
    )
    result = oa.optimize_anything(
        seed_candidate={"prompt": seed},
        evaluator=evaluate,
        dataset=[item.to_record() for item in development],
        valset=[item.to_record() for item in validation],
        objective="Improve complete multi-turn EMI recovery episodes: correct final state and tools first, then concise experience, with zero new severe regression.",
        background="EVA-inspired validation plus tau-style environment/action/communication checks. Hidden state is evaluator-only. This is text-proxy development evidence, not voice lift.",
        config=config,
    )
    best = result.best_candidate["prompt"] if isinstance(result.best_candidate, dict) else str(result.best_candidate)
    candidate_artifact = write_text(OUTPUT / "finalist.md", best)
    lineage = {
        "schema_version": "dynamic-gepa-lineage.v1",
        "optimizer": "gepa.optimize_anything",
        "gepa_version": "0.1.4",
        "agent_model": agent_client.model,
        "reflection_model": reflection_client.model,
        "seed_path": str(seed_path),
        "seed_sha256": hashlib.sha256(seed.encode()).hexdigest(),
        "dataset_id": "emi_dynamic_v1",
        "dataset_manifest_sha256": hashlib.sha256((SCENARIOS / "manifest.json").read_bytes()).hexdigest(),
        "candidate_artifact": candidate_artifact,
        "deployability_issues": lint_deployable_candidate(best),
        "train_scenario_ids": [item.scenario_id for item in development],
        "validation_scenario_ids": [item.scenario_id for item in validation],
        "held_out_accessed": False,
        "max_metric_calls": max_metric_calls,
        "max_candidate_proposals": max_proposals,
        "acceptance_criterion": "strict_improvement",
        "native_tracking": {
            "provider": "gepa.optimize_anything.TrackingConfig",
            "backend": "mlflow",
            "experiment": "the framework Dynamic GEPA",
        },
        "engine_candidate_count": len(getattr(result, "candidates", [])),
        "best_candidate_index": int(getattr(result, "best_idx", 0)),
        "reflections": proposer.reflections,
        "evaluations": evaluations,
        "claim_boundary": "Stateful development/validation search only. Regression, fresh final, and matched voice gates remain mandatory.",
    }
    write_json(OUTPUT / "lineage.json", lineage)
    lineage["mlflow"] = log_optimizer(lineage, OUTPUT)
    write_json(OUTPUT / "lineage.json", lineage)
    return lineage


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--max-metric-calls", type=int, default=24)
    parser.add_argument("--max-proposals", type=int, default=2)
    args = parser.parse_args()
    result = run(args.seed, args.max_metric_calls, args.max_proposals)
    print(json.dumps({key: result[key] for key in ("optimizer", "candidate_artifact", "engine_candidate_count", "deployability_issues", "claim_boundary", "mlflow")}, indent=2))


if __name__ == "__main__":
    main()
