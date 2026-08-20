"""Compare two completed matched EVA–Samvaad suites and write the release record."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from framework.evaluation.live_release import compare_live_suites


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "artifacts" / "framework" / "emi" / "matched_live_release.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = compare_live_suites(args.baseline, args.candidate)
    result["decided_at"] = datetime.now(UTC).isoformat()
    result["baseline_run_directory"] = str(args.baseline.resolve())
    result["candidate_run_directory"] = str(args.candidate.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "matched_trials": result["matched_trials"]}, indent=2))


if __name__ == "__main__":
    main()

