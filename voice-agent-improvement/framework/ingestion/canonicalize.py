"""Convert Sarvam-specific baseline artifacts into framework-native traces."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from framework.core.io import manifest, read_jsonl, write_json, write_jsonl
from framework.core.schemas import CanonicalTrace, ReferenceAnnotation
from framework.domain import load_domain_pack


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CALLS = ROOT / "artifacts" / "baseline" / "calls.jsonl"
DEFAULT_SCORECARDS = ROOT / "artifacts" / "baseline" / "scorecards.jsonl"
DEFAULT_ANNOTATIONS = ROOT / "improvement" / "human_annotations.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "framework" / "emi"


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonicalize(
    calls_path: Path = DEFAULT_CALLS,
    scorecards_path: Path = DEFAULT_SCORECARDS,
    annotations_path: Path = DEFAULT_ANNOTATIONS,
    output_dir: Path = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    pack = load_domain_pack("emi_recovery")
    calls = read_jsonl(calls_path)
    scores = {row["run_id"]: row for row in read_jsonl(scorecards_path)}
    annotations = {row["run_id"]: row for row in json.loads(annotations_path.read_text(encoding="utf-8"))}
    if set(annotations) != {call["run_id"] for call in calls}:
        raise ValueError("baseline calls and provisional annotations do not have identical run_id sets")

    source_hashes = {
        "calls_sha256": _file_hash(calls_path),
        "scorecards_sha256": _file_hash(scorecards_path),
        "annotations_sha256": _file_hash(annotations_path),
    }
    traces: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    for call in calls:
        run_id = call["run_id"]
        attempt = call.get("attempt", {})
        variables = attempt.get("agent_variables", {})
        score = scores.get(run_id, {})
        turns = []
        for message in call["messages"]:
            turns.append(
                {
                    "turn_id": int(message["turn_id"]),
                    "actor": "agent" if message["role"] == "assistant" else "caller",
                    "content": str(message.get("content", "")),
                    "language": message.get("language_name") or attempt.get("language_name"),
                    "timestamp": message.get("timestamp"),
                }
            )
        trace = CanonicalTrace(
            schema_version="canonical-voice-trace.v1",
            trace_id=run_id,
            domain_id=pack.domain_id,
            domain_pack_version=pack.version,
            source={
                "platform": call.get("source", {}).get("platform", "sarvam_indus"),
                "app_version": call.get("source", {}).get("app_version"),
                "attempt_id": call.get("source", {}).get("attempt_id"),
                "interaction_id": call.get("source", {}).get("interaction_id"),
                "recording_type": "real_voice",
            },
            context={
                "scenario_id": call.get("scenario_id"),
                "corpus_role": call.get("corpus_role"),
                "benchmark_member": bool(call.get("benchmark_member")),
                "primary_eligible": bool(call.get("primary_eligible")),
                "expected_disposition": call.get("expected_disposition"),
                "agent_variables": variables,
            },
            turns=turns,
            observed_outcome={
                "actual_disposition": variables.get("disposition"),
                "call_summary": variables.get("callSummary"),
                "duration_seconds": attempt.get("duration_in_seconds"),
                "ended_by": attempt.get("ended_by"),
                "automated": score.get("automated", {}),
            },
            lineage={**source_hashes, "original_record_sha256": call.get("record_sha256")},
        )
        annotation = annotations[run_id]
        reference = ReferenceAnnotation(
            schema_version="reference-annotation.v1",
            trace_id=run_id,
            review_status="provisional",
            labels={key: value for key, value in annotation.items() if key != "run_id"},
            provenance={
                "annotator": "codex_assisted",
                "independent_human_review": False,
                "source_annotation_sha256": source_hashes["annotations_sha256"],
                "warning": "Baseline labels are provisional reference annotations, not gold truth, until reviewed by the project owner.",
            },
        )
        traces.append(trace.to_record())
        references.append(reference.to_record())

    trace_artifact = write_jsonl(output_dir / "traces.jsonl", traces)
    reference_artifact = write_jsonl(output_dir / "reference_annotations.provisional.jsonl", references)
    pack_artifact = write_json(output_dir / "domain_pack.snapshot.json", pack.to_record())
    stage_manifest = manifest(
        "canonicalize",
        [trace_artifact, reference_artifact, pack_artifact],
        input_hashes=source_hashes,
        domain_id=pack.domain_id,
        domain_pack_version=pack.version,
        reference_status="provisional",
    )
    write_json(output_dir / "canonicalization.manifest.json", stage_manifest)
    return stage_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calls", type=Path, default=DEFAULT_CALLS)
    parser.add_argument("--scorecards", type=Path, default=DEFAULT_SCORECARDS)
    parser.add_argument("--annotations", type=Path, default=DEFAULT_ANNOTATIONS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(canonicalize(args.calls, args.scorecards, args.annotations, args.output_dir), indent=2))


if __name__ == "__main__":
    main()
