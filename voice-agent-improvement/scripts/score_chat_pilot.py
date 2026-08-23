"""Grade a chat-pilot run with the frozen evaluator and emit the full panel."""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from framework.evaluation.adapters.chat_console import build_run
from framework.evaluation.contracts import EvaluationScenario, UserStep
from framework.evaluation.metrics import aggregate, evaluate_run

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "artifacts" / "framework" / "emi" / "benchmark_v1" / "development.jsonl"


def load_scenarios() -> dict[str, EvaluationScenario]:
    out = {}
    for line in BENCH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        out[rec["scenario_id"]] = EvaluationScenario.from_record(rec)
    return out


def main() -> None:
    run_name = sys.argv[1]
    src = ROOT / "artifacts" / "campaign2" / "chat_pilot" / f"{run_name}.jsonl"
    scenarios = load_scenarios()
    evaluations, runs = [], []
    for line in src.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        sid = rec["scenario"]["id"]
        scenario = scenarios[sid]
        run = build_run(
            scenario_id=sid,
            candidate_id=run_name,
            transcript=rec.get("transcript") or "",
            caller_steps=rec["scenario"]["steps"],
            ledger=rec["effects"],
            initial_state=scenario.initial_environment,
        )
        runs.append(run)
        evaluations.append(evaluate_run(scenario, run))
    summary = aggregate(evaluations)
    out = ROOT / "artifacts" / "campaign2" / "chat_pilot" / f"{run_name}.eva.json"
    out.write_text(json.dumps({"run": run_name, "summary": summary,
                               "per_scenario": evaluations}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False)[:2600])


if __name__ == "__main__":
    main()
