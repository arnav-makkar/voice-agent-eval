"""Run a prompt candidate through the stateful EMI evaluation suite."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from framework.adapters.gemini import GeminiJsonClient, load_env_file
from framework.experiments.tracking import log_dynamic_evaluation

from .candidates import GeminiPromptAgent
from .runner import load_scenarios, run_suite


ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ROOT / "artifacts" / "framework" / "emi" / "dynamic_scenarios_v1"
DEFAULT_PROMPT = ROOT / "agent" / "v1" / "SYSTEM-PROMPT.md"
OUTPUT = ROOT / "artifacts" / "framework" / "emi" / "dynamic_experiments"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-id", default="v12-dynamic-baseline")
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--splits", default="development,validation,regression")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--model", default="gemini-3.6-flash")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    load_env_file(ROOT / ".env")
    prompt = args.prompt.read_text(encoding="utf-8")
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    split_names = [item.strip() for item in args.splits.split(",") if item.strip()]
    scenarios = []
    for split in split_names:
        scenarios.extend(load_scenarios(SCENARIOS / f"{split}.jsonl"))
    if args.limit:
        scenarios = scenarios[: args.limit]
    fresh_final_access = None
    if "fresh_final" in split_names:
        seal = json.loads((SCENARIOS / "fresh_final_seal.json").read_text(encoding="utf-8"))
        allowed = {seal["baseline_frozen_sha256"], seal["candidate_method_frozen_sha256"]}
        if prompt_hash not in allowed:
            raise RuntimeError("fresh final is sealed for the frozen baseline and finalist only")
        access_path = SCENARIOS / "fresh_final_access_log.json"
        fresh_final_access = json.loads(access_path.read_text(encoding="utf-8"))
        if any(item.get("candidate_hash") == prompt_hash for item in fresh_final_access["evaluation_runs"]):
            raise RuntimeError("this frozen candidate has already accessed the fresh final test")
    run_stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output = args.output or OUTPUT / f"{args.candidate_id}-{run_stamp}"
    client = GeminiJsonClient(model=args.model, cache_dir=ROOT / "artifacts" / "framework" / "cache")
    candidate = GeminiPromptAgent(args.candidate_id, prompt, client)
    summary = run_suite(candidate, prompt, scenarios, output)
    summary["dataset_id"] = "emi_dynamic_v1"
    summary["experiment_id"] = output.name
    summary["model"] = args.model
    summary["prompt_path"] = str(args.prompt)
    summary["prompt_sha256"] = prompt_hash
    summary["mlflow"] = log_dynamic_evaluation(summary, output)
    from framework.core.io import write_json
    write_json(output / "summary.json", summary)
    if fresh_final_access is not None:
        fresh_final_access["accessed_by_improvement"] = False
        fresh_final_access["evaluation_runs"].append(
            {
                "candidate_id": args.candidate_id,
                "candidate_hash": prompt_hash,
                "experiment_id": summary["experiment_id"],
                "completed_at": datetime.now(UTC).isoformat(),
            }
        )
        write_json(SCENARIOS / "fresh_final_access_log.json", fresh_final_access)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
