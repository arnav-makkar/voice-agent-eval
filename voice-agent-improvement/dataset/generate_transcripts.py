"""Generate auditable fixture or two-model synthetic transcript JSONL."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dataset.simulation import OpenAICompatibleJsonModel, run_fixture_rollout, run_model_rollout


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIOS = ROOT / "dataset" / "scenarios-v2.jsonl"
DEFAULT_OUTPUT = ROOT / "dataset" / "transcripts" / "fixture-v10.jsonl"
DEFAULT_PROMPT = ROOT / "agent" / "v1" / "SYSTEM-PROMPT.md"
DEFAULT_INITIAL_MESSAGE = ROOT / "agent" / "v1" / "INITIAL-MESSAGE.txt"


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--agent-prompt", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--initial-message", type=Path, default=DEFAULT_INITIAL_MESSAGE)
    parser.add_argument("--candidate-id", default="indus-v10")
    parser.add_argument("--split", choices=["all", "development", "regression", "held_out"], default="all")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--provider", choices=["fixture", "openai-compatible"], default="fixture")
    parser.add_argument("--base-url", default=os.environ.get("SIM_LLM_BASE_URL", "https://api.openai.com/v1"))
    parser.add_argument("--caller-model", default=os.environ.get("SIM_CALLER_MODEL", ""))
    parser.add_argument("--agent-model", default=os.environ.get("SIM_AGENT_MODEL", ""))
    parser.add_argument("--api-key-env", default="SIM_LLM_API_KEY")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if args.output.exists() and not args.overwrite:
        parser.error(f"output already exists: {args.output}; pass --overwrite to replace it")
    scenarios = read_jsonl(args.scenarios)
    if args.split != "all":
        scenarios = [item for item in scenarios if item["split"] == args.split]
    if args.limit is not None:
        if args.limit < 1:
            parser.error("--limit must be positive")
        scenarios = scenarios[: args.limit]
    if not scenarios:
        parser.error("no scenarios selected")

    candidate_prompt = args.agent_prompt.read_text(encoding="utf-8")
    initial_message = args.initial_message.read_text(encoding="utf-8")
    caller_model = agent_model = None
    if args.provider == "openai-compatible":
        api_key = os.environ.get(args.api_key_env, "")
        if not api_key:
            parser.error(f"set {args.api_key_env} before using --provider openai-compatible")
        if not args.caller_model or not args.agent_model:
            parser.error("--caller-model and --agent-model are required for model generation")
        caller_model = OpenAICompatibleJsonModel(
            base_url=args.base_url, api_key=api_key, model_name=args.caller_model
        )
        agent_model = OpenAICompatibleJsonModel(
            base_url=args.base_url, api_key=api_key, model_name=args.agent_model
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for scenario in scenarios:
            if args.provider == "fixture":
                record = run_fixture_rollout(
                    scenario,
                    candidate_id=args.candidate_id,
                    candidate_prompt=candidate_prompt,
                    initial_message=initial_message,
                )
            else:
                assert caller_model is not None and agent_model is not None
                record = run_model_rollout(
                    scenario,
                    candidate_id=args.candidate_id,
                    candidate_prompt=candidate_prompt,
                    initial_message=initial_message,
                    caller_model=caller_model,
                    agent_model=agent_model,
                )
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"wrote {len(scenarios)} {args.provider} transcripts to {args.output}")


if __name__ == "__main__":
    main()
