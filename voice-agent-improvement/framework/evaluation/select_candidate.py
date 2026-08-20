"""Select a finalist from independently gated repair arms without test-set access."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from framework.core.io import write_json


def choose(arms: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [arm for arm in arms if arm["release"]["decision"] == "eligible_for_fresh_final_test"]
    if not eligible:
        raise RuntimeError("no candidate is eligible for fresh final")
    ranked = sorted(
        eligible,
        key=lambda arm: (
            arm["release"].get("candidate_task_successes", 0),
            arm.get("semantic", {}).get("average_progression", 0),
            arm["release"].get("candidate_experience", 0),
            -arm.get("prompt_bytes", 0),
        ),
        reverse=True,
    )
    winner = ranked[0]
    return {
        "schema_version": "candidate-selection.v1",
        "selected_candidate_id": winner["candidate_id"],
        "selected_prompt_path": winner["prompt_path"],
        "selected_prompt_sha256": winner["prompt_sha256"],
        "release_decision_path": winner["release_path"],
        "ranking_policy": [
            "must be eligible under strict paired release gate",
            "maximize exact task successes",
            "then semantic conversation progression",
            "then deterministic experience",
            "then smaller prompt as a complexity tie-break",
        ],
        "arms": arms,
        "claim_boundary": "Selection used development/validation/regression evidence only; fresh-final cards were not yet created or accessed.",
    }


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", action="append", nargs=5, metavar=("ID", "PROMPT", "SUMMARY", "SEMANTIC", "RELEASE"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    arms = []
    for candidate_id, prompt_raw, summary_raw, semantic_raw, release_raw in args.arm:
        prompt = Path(prompt_raw).resolve()
        summary = _read(Path(summary_raw))
        semantic = _read(Path(semantic_raw))
        release_path = Path(release_raw).resolve()
        release = _read(release_path)
        arms.append(
            {
                "candidate_id": candidate_id,
                "prompt_path": str(prompt),
                # Rescore summaries intentionally describe the immutable trace bundle
                # and may not repeat the prompt hash.  Hash the actual candidate file
                # so selection and the later method freeze are independently auditable.
                "prompt_sha256": hashlib.sha256(prompt.read_bytes()).hexdigest(),
                "prompt_bytes": prompt.stat().st_size,
                "release_path": str(release_path),
                "release": release,
                "semantic": {
                    "average_progression": semantic.get("average_progression"),
                    "average_faithfulness": semantic.get("average_faithfulness"),
                    "average_conciseness": semantic.get("average_conciseness"),
                    "factual_errors": semantic.get("factual_errors"),
                    "integrity_violations": semantic.get("integrity_violations"),
                    "forbidden_behavior_violations": semantic.get("forbidden_behavior_violations"),
                },
            }
        )
    result = choose(arms)
    result["selected_at"] = datetime.now(UTC).isoformat()
    write_json(args.output, result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
