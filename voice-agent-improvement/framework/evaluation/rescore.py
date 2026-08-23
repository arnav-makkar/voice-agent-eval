"""Recompute deterministic metrics without mutating historical run evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from framework.core.io import read_jsonl, write_json, write_jsonl
from framework.evaluation.contracts import EvaluationScenario, ScenarioRun
from framework.evaluation.metrics import aggregate, evaluate_run


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCENARIOS = ROOT / "artifacts" / "framework" / "emi" / "dynamic_scenarios_v1"


def _index(scenario_dir: Path) -> dict[str, EvaluationScenario]:
    result: dict[str, EvaluationScenario] = {}
    for path in scenario_dir.glob("*.jsonl"):
        for record in read_jsonl(path):
            scenario = EvaluationScenario.from_record(record)
            result[scenario.scenario_id] = scenario
    return result


def rescore(run_path: Path, output_dir: Path, scenario_dir: Path = DEFAULT_SCENARIOS) -> dict:
    scenarios = _index(scenario_dir)
    run_records = read_jsonl(run_path)
    metrics = []
    for record in run_records:
        scenario_id = record["scenario_id"]
        if scenario_id not in scenarios:
            raise KeyError(f"scenario not found for rescore: {scenario_id}")
        metrics.append(evaluate_run(scenarios[scenario_id], ScenarioRun.from_record(record)))
    evaluator_paths = [
        Path(__file__).with_name("metrics.py"),
        Path(__file__).with_name("contracts.py"),
        Path(__file__).with_name("environment.py"),
    ]
    evaluator_hash = hashlib.sha256(b"".join(path.read_bytes() for path in evaluator_paths)).hexdigest()
    summary = {
        "schema_version": "deterministic-rescore.v1",
        "evaluator_version": "evaluation-metrics.v3/framework-eva-adapter.v1",
        "evaluator_sha256": evaluator_hash,
        "source_runs": str(run_path),
        "source_runs_sha256": hashlib.sha256(run_path.read_bytes()).hexdigest(),
        "aggregate": aggregate(metrics),
        "claim_boundary": "Deterministic rescore of immutable episode traces; it does not rerun the agent or simulator.",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "metrics.jsonl", metrics)
    write_json(output_dir / "summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_path", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--scenario-dir", type=Path, default=DEFAULT_SCENARIOS)
    args = parser.parse_args()
    print(json.dumps(rescore(args.run_path, args.output_dir, args.scenario_dir), indent=2))


if __name__ == "__main__":
    main()
