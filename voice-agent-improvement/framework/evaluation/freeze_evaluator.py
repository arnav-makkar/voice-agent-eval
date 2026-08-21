"""Freeze the evaluator contract before running another improvement cycle."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from framework.core.io import write_json


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VERSION = 13


def _default_output(version: int) -> Path:
    return ROOT / "artifacts" / "framework" / "emi" / f"eva_adapter_v{version}" / "evaluator_freeze.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze(output: Path, *, version: int = DEFAULT_VERSION) -> dict:
    if output.exists():
        raise FileExistsError("evaluator freeze already exists; create a new version instead of overwriting")
    evaluator_paths = [
        ROOT / "framework" / "adapters" / "gemini.py",
        *[
        ROOT / "framework" / "evaluation" / name
        for name in (
            "contracts.py",
            "environment.py",
            "metrics.py",
            "semantic_metrics.py",
            "adaptive_caller.py",
            "live_budget.py",
            "live_release.py",
            "adapters/indus.py",
            "adapters/sarvam_speech.py",
        )
        ],
        ROOT / "scripts" / "run_eva_samvaad_live.py",
        ROOT / "scripts" / "run_eva_samvaad_suite.py",
        ROOT / "scripts" / "rescore_eva_samvaad_run.py",
        ROOT / "scripts" / "build_eva_emi_voice_suite.py",
        ROOT / "scripts" / "build_eva_hinglish_voice_suite.py",
        ROOT / "scripts" / "build_eva_hinglish_voice_suite_v3.py",
        ROOT / "scripts" / "audit_eva_voice_run.py",
        ROOT / "scripts" / "compare_eva_samvaad_suites.py",
        ROOT / "framework" / "tool_service.py",
        ROOT / "research" / "upstream" / "eva" / "src" / "eva" / "assistant" / "samvaad_server.py",
        ROOT / "research" / "upstream" / "eva" / "src" / "eva" / "metrics" / "accuracy" / "faithfulness.py",
        ROOT / "research" / "upstream" / "eva" / "configs" / "prompts" / "judge.yaml",
    ]
    scenario_paths = [
        ROOT / "artifacts" / "framework" / "emi" / "dynamic_scenarios_v1" / name
        for name in ("development.jsonl", "validation.jsonl", "regression.jsonl", "manifest.json", "validation.json")
    ]
    voice_suite_paths = [
        ROOT / "research" / "upstream" / "eva" / "data" / "emi_dataset.json",
        ROOT / "artifacts" / "framework" / "emi" / "eva_voice_suite_v3_hinglish_fixed" / "manifest.json",
        *sorted((ROOT / "research" / "upstream" / "eva" / "data" / "emi_scenarios").glob("EMI-HINGLISH-FIXED-*.json")),
    ]
    components = {
        "evaluator_files": [{"path": str(path), "sha256": _sha(path)} for path in evaluator_paths],
        "scenario_suite": [{"path": str(path), "sha256": _sha(path)} for path in scenario_paths],
        "live_voice_suite": [{"path": str(path), "sha256": _sha(path)} for path in voice_suite_paths],
    }
    bundle_hash = hashlib.sha256(
        json.dumps(components, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if version == 13:
        supersedes = (
            "eva_adapter_v12: V13 preserves the failed v19/v2 pilot unchanged, rebases stale relative-date facts into "
            "new record IDs, and adds a deterministic post-flight for missing tools, unsupported terminal claims and "
            "non-Hinglish Indic-script switches. V13 has no live score until a separately authorised rerun."
        )
    elif version == 12:
        supersedes = (
            "eva_adapter_v11: V12 preserves all scoring and execution-truth rules and changes only the active prospective "
            "voice corpus to a separately versioned Hinglish-only suite. The multilingual V1 suite, V10/V11 freezes and "
            "historical Punjabi pilot remain immutable; none is relabelled as V12 evidence."
        )
    elif version == 11:
        supersedes = (
            "eva_adapter_v10: V11 is the post-pilot evaluator. It adds NA/null output-sentinel "
            "normalisation in the Samvaad adapter and the audited terminal-disposition endpoint in "
            "the isolated tool service. V10 and both pilot runs remain immutable under their original "
            "hashes; V11 governs only the next repair rerun."
        )
    elif version == 10:
        supersedes = (
            "eva_adapter_v9: V10 changes only the prospective synthetic caller identity from "
            "'Arnav Dhavala' to 'Arnav' across the 18-record voice suite and its generator. "
            "Evaluation metrics, transport, state isolation, tool rules and release gates are unchanged. "
            "V9 and the historical V7 live result remain immutable."
        )
    else:
        supersedes = (
            "eva_adapter_v8: V9 preserves the V8 transport, deterministic acoustic perturbations, "
            "18-record matched voice suite, isolated live tool service, budgeted suite runner, and exact "
            "live release gate. It adds an explicit, default-off synthetic tool-auth bypass for controlled "
            "evaluation environments after the Indus test runtime failed to propagate stored credentials. "
            "V8 remains immutable; the preserved one-call smoke result remains under V7."
        )
    record = {
        "schema_version": "evaluator-freeze.v1",
        "evaluator_version": f"evaluation-metrics.v3/loopline-eva-adapter.v1/samvaad-duplex.v{version}",
        "status": "frozen_for_next_loop",
        "frozen_at": datetime.now(UTC).isoformat(),
        "components": components,
        "bundle_sha256": bundle_hash,
        "taxonomy": {
            "accuracy": ["task_completion", "faithfulness", "agent_speech_fidelity"],
            "experience": ["conciseness", "conversation_progression", "turn_taking"],
            "validation": ["conversation_finished", "user_behavioral_fidelity", "user_speech_fidelity"],
            "diagnostic": ["tool_call_validity", "response_speed", "stt_wer", "speakability", "transcription_accuracy_key_entities"],
        },
        "source_attribution": {
            "eva": {"commit": "e0041e3d9d4e706b21630a3ecb7595855004d63f", "license": "MIT", "use": "metric taxonomy, evaluation runtime, and documented Samvaad-specific judge adaptation"},
            "tau": {"commit": "a2c024725189473d2d7cea3a5cfdbcc67478e41f", "license": "MIT", "use": "state/action assertions and simulator concepts"},
            "implementation": "project-owned Indus integration with disclosed MIT-licensed EVA adaptations preserved in the pinned checkout",
        },
        "supersedes": supersedes,
        "release_rules": {
            "validation_before_scoring": True,
            "deterministic_execution_truth_is_primary": True,
            "llm_judges_are_secondary": True,
            "missing_voice_evidence_is_not_a_pass": True,
            "improvement_cannot_mutate_evaluator": True,
        },
        "claim_boundary": "This freezes the next-loop evaluator implementation. Historical results remain under their original evaluator version and must not be relabelled as voice evidence.",
    }
    write_json(output, record)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", type=int, default=DEFAULT_VERSION)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.version < 1:
        parser.error("--version must be a positive integer")
    output = args.output or _default_output(args.version)
    print(json.dumps(freeze(output, version=args.version), indent=2))


if __name__ == "__main__":
    main()
