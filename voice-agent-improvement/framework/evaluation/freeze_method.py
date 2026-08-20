"""Freeze candidate-selection and evaluator artifacts before fresh-final access."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from framework.core.io import write_json


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "artifacts" / "framework" / "emi" / "method_freeze.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze(baseline: Path, finalist: Path, selection_decision: Path, output: Path = DEFAULT_OUTPUT) -> dict:
    if output.exists():
        raise FileExistsError("method freeze already exists; create a versioned path instead of overwriting")
    evaluator_paths = [
        ROOT / "framework" / "evaluation" / name
        for name in ("contracts.py", "environment.py", "runner.py", "metrics.py", "semantic_metrics.py", "release.py")
    ]
    scenario_paths = [
        ROOT / "artifacts" / "framework" / "emi" / "dynamic_scenarios_v1" / name
        for name in ("development.jsonl", "validation.jsonl", "regression.jsonl", "manifest.json", "validation.json")
    ]
    components = {
        "baseline_prompt": {"path": str(baseline), "sha256": _sha(baseline)},
        "finalist_prompt": {"path": str(finalist), "sha256": _sha(finalist)},
        "selection_decision": {"path": str(selection_decision), "sha256": _sha(selection_decision)},
        "evaluator_files": [{"path": str(path), "sha256": _sha(path)} for path in evaluator_paths],
        "development_suite": [{"path": str(path), "sha256": _sha(path)} for path in scenario_paths],
    }
    bundle_hash = hashlib.sha256(json.dumps(components, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    evaluator_hash = hashlib.sha256(b"".join(path.read_bytes() for path in evaluator_paths)).hexdigest()
    record = {
        "schema_version": "evaluation-method-freeze.v1",
        "frozen_at": datetime.now(UTC).isoformat(),
        "components": components,
        "baseline_prompt_sha256": components["baseline_prompt"]["sha256"],
        "finalist_prompt_sha256": components["finalist_prompt"]["sha256"],
        "evaluator_bundle_sha256": evaluator_hash,
        "method_bundle_sha256": bundle_hash,
        "access_policy": "Only the frozen baseline and finalist may run once on fresh_final; no repair process receives final-test feedback.",
        "claim_boundary": "Automated hash freeze. Owner semantic review of generated final cards remains a separate human gate.",
    }
    write_json(output, record)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--finalist", type=Path, required=True)
    parser.add_argument("--selection-decision", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(freeze(args.baseline, args.finalist, args.selection_decision, args.output), indent=2))


if __name__ == "__main__":
    main()
