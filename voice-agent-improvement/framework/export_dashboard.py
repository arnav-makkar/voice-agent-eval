"""Merge framework artifacts into the existing redacted Loopline snapshot."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from framework.core.io import write_json
from framework.repairs.registry import list_repair_engines


ROOT = Path(__file__).resolve().parents[1]
FRAMEWORK = ROOT / "artifacts" / "framework"
DEFAULT_DASHBOARD = ROOT.parent / "dashboard" / "public" / "dashboard-data.json"


def _read(path: Path, default: Any = None) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _dynamic_candidate(run_dir: Path) -> dict[str, Any] | None:
    summary = _read(run_dir / "summary.json", None)
    if not summary:
        return None
    rescore = _read(run_dir / "rescore-v3" / "summary.json", {}) or _read(run_dir / "rescore-v2" / "summary.json", {})
    semantic = _read(run_dir / "semantic-v2" / "semantic_summary.json", {})
    return {
        "candidateId": summary.get("candidate_id"),
        "experimentId": summary.get("experiment_id"),
        "promptHash": summary.get("prompt_sha256") or summary.get("candidate_hash"),
        "promptPath": summary.get("prompt_path"),
        "model": summary.get("model"),
        "aggregate": rescore.get("aggregate") or summary.get("aggregate", {}),
        "deterministicEvaluator": {
            "version": rescore.get("evaluator_version"),
            "hash": rescore.get("evaluator_sha256"),
        },
        "semantic": semantic,
        "mlflow": summary.get("mlflow", {}),
        "claimBoundary": summary.get("claim_boundary"),
    }


def _dynamic_episodes(run_dir: Path, scenarios: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    run_role = _read(run_dir / "calibration_status.json", {})
    runs = {item["scenario_id"]: item for item in _read_jsonl(run_dir / "runs.jsonl")}
    metric_path = run_dir / "rescore-v3" / "metrics.jsonl"
    if not metric_path.exists():
        metric_path = run_dir / "rescore-v2" / "metrics.jsonl"
    if not metric_path.exists():
        metric_path = run_dir / "metrics.jsonl"
    metrics = {item["scenario_id"]: item for item in _read_jsonl(metric_path)}
    semantic_path = run_dir / "semantic-v2" / "semantic_metrics.jsonl"
    semantic_metrics = {item["scenario_id"]: item for item in _read_jsonl(semantic_path)}
    result = []
    for scenario_id, run in runs.items():
        scenario = scenarios.get(scenario_id, {})
        score = metrics.get(scenario_id, {})
        semantic = semantic_metrics.get(scenario_id, {})
        eva = score.get("eva") or {
            "accuracy": {
                "task_completion": {"score": 1.0 if score.get("task_success") else 0.0},
                "faithfulness": {"score": semantic.get("faithfulness_score", 0) / 4 if semantic else None},
                "agent_speech_fidelity": {"score": None, "status": "voice_run_required"},
            },
            "experience": {
                "conciseness": {"score": semantic.get("conciseness_score", 0) / 4 if semantic else score.get("experience", {}).get("score")},
                "conversation_progression": {"score": semantic.get("conversation_progression_score", 0) / 4 if semantic else None},
                "turn_taking": {"score": None, "status": "voice_run_required"},
            },
            "validation": {
                "conversation_finished": run.get("termination_reason") in {"agent_terminal", "caller_terminal"},
                "user_behavioral_fidelity": score.get("valid_simulation"),
            },
            "diagnostic": {
                "tool_call_validity": {
                    "score": (
                        sum(item.get("status") == "success" for item in run.get("tool_events", [])) / len(run.get("tool_events", []))
                        if run.get("tool_events") else None
                    ),
                    "status": "scored" if run.get("tool_events") else "not_exercised",
                },
                "response_speed_ms": score.get("experience", {}).get("average_response_latency_ms"),
                "stt_wer": None,
            },
        }
        result.append(
            {
                "runId": run.get("run_id"),
                "evaluationRole": run_role.get("role", "scored_evaluation"),
                "comparisonEligible": run_role.get("eligible_for_baseline_candidate_comparison", True),
                "scenarioId": scenario_id,
                "candidateId": run.get("candidate_id"),
                "split": scenario.get("split"),
                "family": scenario.get("failure_family"),
                "language": scenario.get("language"),
                "goal": scenario.get("user_goal"),
                "taskSuccess": score.get("task_success"),
                "firstFailure": score.get("first_failure"),
                "failureLocalization": score.get("failure_localization"),
                "experience": score.get("experience", {}),
                "eva": eva,
                "expectedDisposition": (scenario.get("accepted_dispositions") or [None])[0],
                "actualDisposition": run.get("agent_declared_disposition"),
                "terminationReason": run.get("termination_reason"),
                "turns": run.get("turns", []),
                "toolEvents": run.get("tool_events", []),
                "initialState": run.get("initial_state", {}),
                "finalState": run.get("final_state", {}),
                "simulatorValidation": run.get("simulator_validation", {}),
                "provenance": run.get("provenance", {}),
                "audioUrl": run.get("provenance", {}).get("audio_url"),
            }
        )
    return result


def _copy_live_media(episodes: list[dict[str, Any]], dashboard_path: Path) -> None:
    destination = dashboard_path.parent / "evidence"
    for episode in episodes:
        provenance = episode.get("provenance", {})
        artifact = provenance.get("audio_artifact")
        if not artifact:
            continue
        source = Path(str(artifact))
        caption = Path(str(provenance.get("caption_artifact") or f"{source}.vtt"))
        if not source.exists():
            continue
        destination.mkdir(parents=True, exist_ok=True)
        audio_target = destination / source.name
        shutil.copy2(source, audio_target)
        if caption.exists():
            shutil.copy2(caption, destination / caption.name)
        episode["audioUrl"] = f"/evidence/{audio_target.name}"


def export(path: Path = DEFAULT_DASHBOARD) -> dict[str, Any]:
    snapshot = _read(path, {})
    dataset_dir = FRAMEWORK / "emi" / "datasets" / "emi_failure_derived_v3"
    dataset_manifest = _read(dataset_dir / "manifest.json", {})
    validation = _read(dataset_dir / "validation.json", {})
    integrity_audit = _read(dataset_dir / "integrity_audit.json", {})
    calibration = _read(FRAMEWORK / "emi" / "evaluator_calibration" / "summary.json", {})
    diagnosis = _read(FRAMEWORK / "emi" / "diagnosis" / "summary.json", {})
    extractor_runs = []
    for summary_path in sorted((FRAMEWORK / "emi" / "extractor").glob("*/summary.json")):
        summary = _read(summary_path, {})
        extractor_runs.append(
            {
                "candidateId": summary.get("candidate_id"),
                "platformAccuracy": summary.get("platform_baseline_accuracy"),
                "candidateAccuracy": summary.get("candidate_accuracy"),
                "unsupportedSummaryRate": summary.get("candidate_unsupported_summary_rate"),
                "invalidEnumCount": summary.get("candidate_invalid_enum_count"),
                "claimBoundary": summary.get("claim_boundary"),
            }
        )
    experiments = []
    for summary_path in sorted((FRAMEWORK / "emi" / "experiments").glob("*/summary.json")):
        summary = _read(summary_path, {})
        experiments.append(
            {
                "experimentId": summary.get("experiment_id"),
                "candidateId": summary.get("candidate_id"),
                "datasetId": summary.get("dataset_id"),
                "splits": summary.get("splits", []),
                "promptHash": summary.get("candidate_prompt_sha256"),
                "summary": summary.get("summary", {}),
                "mlflow": summary.get("mlflow", {}),
            }
        )
    gepa = _read(FRAMEWORK / "emi" / "gepa" / "lineage.json", {})
    gepa_deployable = _read(FRAMEWORK / "emi" / "gepa" / "deployable-finalist.json", {})
    release = _read(FRAMEWORK / "emi" / "release" / "decision.json", {})
    portability = _read(FRAMEWORK / "hospital_appointments" / "summary.json", {})
    invalid_v1 = _read(FRAMEWORK / "emi" / "datasets" / "emi_failure_derived_v1" / "semantic_audit.json", {})
    invalid_v2 = _read(FRAMEWORK / "emi" / "datasets" / "emi_failure_derived_v2" / "semantic_audit.json", {})
    v3_experiment_count = sum(item.get("datasetId") == "emi_failure_derived_v3" for item in experiments)
    dynamic_root = FRAMEWORK / "emi" / "dynamic_experiments"
    dynamic_candidates = [
        item
        for item in (
            _dynamic_candidate(dynamic_root / "v12-dynamic-full"),
            _dynamic_candidate(dynamic_root / "v13-stateful-v2"),
            _dynamic_candidate(dynamic_root / "v14-terminal-discipline-full"),
            _dynamic_candidate(dynamic_root / "v15-firm-today-full"),
            _dynamic_candidate(dynamic_root / "dynamic-gepa-finalist-full"),
        )
        if item
    ]
    selection = _read(FRAMEWORK / "emi" / "selection.json", {})
    selected_id = selection.get("selected_candidate_id") or "v15-firm-today"
    scenario_records: dict[str, dict[str, Any]] = {}
    dynamic_scenario_dir = FRAMEWORK / "emi" / "dynamic_scenarios_v1"
    for split in ("development", "validation", "regression", "fresh_final"):
        for item in _read_jsonl(dynamic_scenario_dir / f"{split}.jsonl"):
            scenario_records[item["scenario_id"]] = item
    candidate_dir_by_id = {item["candidateId"]: dynamic_root / item["experimentId"] for item in dynamic_candidates}
    episode_dirs = [dynamic_root / "v12-dynamic-full"]
    if selected_id in candidate_dir_by_id:
        episode_dirs.append(candidate_dir_by_id[selected_id])
    episode_dirs.extend([dynamic_root / "v12-fresh-final", dynamic_root / "v15-fresh-final"])
    dynamic_episodes = []
    for run_dir in episode_dirs:
        dynamic_episodes.extend(_dynamic_episodes(run_dir, scenario_records))
    adaptive_duplex_dirs = sorted((FRAMEWORK / "emi").glob("indus_adaptive_duplex_v*"))
    adaptive_duplex_episodes: list[dict[str, Any]] = []
    for adaptive_dir in adaptive_duplex_dirs:
        directory_episodes = _dynamic_episodes(adaptive_dir, scenario_records)
        _copy_live_media(directory_episodes, path)
        adaptive_duplex_episodes.extend(directory_episodes)
    dynamic_episodes.extend(adaptive_duplex_episodes)
    dynamic_release = _read(FRAMEWORK / "emi" / "dynamic_release_v15.json", {})
    if selection.get("release_decision_path"):
        dynamic_release = _read(Path(selection["release_decision_path"]), dynamic_release)
    dynamic_gepa = _read(FRAMEWORK / "emi" / "dynamic_gepa" / "lineage.json", {})
    fresh_seal = _read(dynamic_scenario_dir / "fresh_final_seal.json", {})
    fresh_access = _read(dynamic_scenario_dir / "fresh_final_access_log.json", {})
    fresh_release = _read(FRAMEWORK / "emi" / "fresh_final_decision.json", {})
    fresh_baseline = _dynamic_candidate(dynamic_root / "v12-fresh-final")
    fresh_candidate = _dynamic_candidate(dynamic_root / "v15-fresh-final")
    indus_live = _read(FRAMEWORK / "emi" / "indus_call_audio_smoke_v2" / "summary.json", {})
    voice_stress_validation = _read(FRAMEWORK / "emi" / "voice_stress_v1" / "validation.json", {})
    voice_stress_live_dir = FRAMEWORK / "emi" / "voice_stress_v1" / "live-v2"
    if not (voice_stress_live_dir / "voice_summary.json").exists():
        voice_stress_live_dir = FRAMEWORK / "emi" / "voice_stress_v1" / "live"
    voice_stress_live = _read(voice_stress_live_dir / "summary.json", {})
    voice_stress_metrics = _read(voice_stress_live_dir / "voice_summary.json", {})
    voice_provider_error = _read(FRAMEWORK / "emi" / "voice_stress_v1" / "live-v2" / "provider_error.json", {})
    adaptive_summaries = [_read(item / "summary.json", {}) for item in adaptive_duplex_dirs]
    adaptive_duplex_summary = next(
        (
            item
            for item in reversed(adaptive_summaries)
            if item.get("aggregate", {}).get("valid_records", 0) > 0
        ),
        adaptive_summaries[-1] if adaptive_summaries else {},
    )
    adaptive_valid_records = adaptive_duplex_summary.get("aggregate", {}).get("valid_records", 0)
    verification = _read(FRAMEWORK / "verification" / "latest.json", {})
    stages = [
        {"id": "ingest", "label": "Canonical traces", "status": "complete", "detail": "20 real V12 calls, hashed and redacted"},
        {"id": "reference", "label": "Reference review", "status": "blocked", "detail": "Provisional labels await owner review"},
        {"id": "dataset", "label": "Static next-turn library", "status": "limited" if validation.get("status") == "pass" else "blocked", "detail": f"{validation.get('total', 0)} development diagnostics; legacy held-out compromised"},
        {"id": "calibration", "label": "Evaluator calibration", "status": "limited", "detail": "Primary/safety calibrated; failure localization advisory"},
        {"id": "experiments", "label": "Offline experiments", "status": "complete" if v3_experiment_count else "running", "detail": f"{v3_experiment_count} valid V3 runs; older V2 runs invalidated"},
        {"id": "gepa", "label": "Stateful GEPA arm", "status": "complete" if dynamic_gepa else "pending", "detail": "28/30 finalist rejected: one P1 state and one P0 guardrail regression"},
        {"id": "release", "label": "Strict paired gate", "status": "complete" if dynamic_release.get("decision") == "eligible_for_fresh_final_test" else "blocked", "detail": f"{dynamic_release.get('decision', 'not run')}; every baseline win preserved"},
        {"id": "evaluation", "label": "Dynamic evaluation engine", "status": "complete" if dynamic_candidates else "building", "detail": f"{len(scenario_records)} stateful cards; deterministic state, action and first-break evidence"},
        {"id": "candidate", "label": "Candidate selection", "status": "complete" if selection else "running", "detail": f"Selected: {selected_id}; manual and GEPA arms compared"},
        {"id": "fresh", "label": "Sealed fresh final", "status": "complete" if fresh_release else "pending", "detail": f"{fresh_release.get('decision', 'pending')}; {fresh_release.get('baseline_task_successes', '—')} → {fresh_release.get('candidate_task_successes', '—')} / {fresh_release.get('matched_scenarios', '—')}"},
        {"id": "voice", "label": "Voice transfer", "status": "limited" if adaptive_valid_records else "building", "detail": f"{adaptive_valid_records} valid adaptive Samvaad duplex calibration run(s); replay audio and paid-session ledger captured; matched baseline/candidate gate remains" if adaptive_valid_records else "Samvaad bidirectional audio harness ready; adaptive live evidence and matched candidate run remain"},
        {"id": "verify", "label": "Reproducibility checks", "status": "complete" if verification.get("passed") else "blocked", "detail": "Python tests, dashboard lint/tests/build, frozen hashes, final protocol, and credential-pattern scan"},
    ]
    snapshot["framework"] = {
        "generatedAt": datetime.now(UTC).isoformat(),
        "frameworkVersion": "1.0.0-interview-mvp",
        "domain": "emi_recovery",
        "dataset": {
            "id": dataset_manifest.get("metadata", {}).get("dataset_id"),
            "validation": validation,
            "heldOutSeal": dataset_manifest.get("metadata", {}).get("held_out_seal_sha256"),
            "referenceStatus": dataset_manifest.get("metadata", {}).get("reference_status"),
            "evidenceType": "static_next_turn_cases",
            "integrityAudit": {
                "groupIndependencePass": integrity_audit.get("group_independence_pass"),
                "legacyHeldOut": integrity_audit.get("legacy_held_out"),
                "requiredReplacement": integrity_audit.get("required_replacement"),
            },
            "invalidatedPredecessors": [item for item in (invalid_v1, invalid_v2) if item],
        },
        "calibration": {
            "referenceStatus": calibration.get("reference_status"),
            "agreement": calibration.get("agreement", {}),
            "interpretation": calibration.get("interpretation"),
        },
        "diagnosis": diagnosis,
        "repairEngines": list_repair_engines(),
        "extractorRuns": extractor_runs,
        "experiments": experiments,
        "gepa": {
            "optimizer": gepa.get("optimizer"),
            "reflectionModel": gepa.get("reflection_model"),
            "candidateCount": gepa.get("engine_candidate_count"),
            "heldOutAccessed": gepa.get("held_out_accessed"),
            "deployabilityIssues": gepa.get("deployability_issues", []),
            "mlflow": gepa.get("mlflow", {}),
            "deployableDerivative": gepa_deployable,
            "claimBoundary": gepa.get("claim_boundary"),
        },
        "release": release,
        "portability": {
            "domain": portability.get("domain_id"),
            "caseCount": portability.get("case_count"),
            "families": portability.get("families", []),
            "claimBoundary": portability.get("claim_boundary"),
        },
        "stages": stages,
        "dynamicEvaluation": {
            "suite": {
                "manifest": _read(dynamic_scenario_dir / "manifest.json", {}),
                "validation": _read(dynamic_scenario_dir / "validation.json", {}),
            },
            "candidates": dynamic_candidates,
            "selectedCandidateId": selected_id,
            "episodes": dynamic_episodes,
            "pairedDecision": dynamic_release,
            "freshComparison": {
                "baseline": fresh_baseline,
                "candidate": fresh_candidate,
                "decision": fresh_release,
            },
        },
        "improvement": {
            "manualCandidate": "v15-firm-today",
            "dynamicGepa": {
                "optimizer": dynamic_gepa.get("optimizer"),
                "gepaVersion": dynamic_gepa.get("gepa_version"),
                "seedSha256": dynamic_gepa.get("seed_sha256"),
                "candidateCount": dynamic_gepa.get("engine_candidate_count"),
                "bestCandidateIndex": dynamic_gepa.get("best_candidate_index"),
                "candidateArtifact": dynamic_gepa.get("candidate_artifact"),
                "deployabilityIssues": dynamic_gepa.get("deployability_issues", []),
                "nativeTracking": dynamic_gepa.get("native_tracking", {}),
                "mlflow": dynamic_gepa.get("mlflow", {}),
                "claimBoundary": dynamic_gepa.get("claim_boundary"),
            },
            "selection": selection,
            "failureDerivedStaticLibrary": {
                "records": validation.get("total", 0),
                "status": "development_diagnostics_only",
                "groupIndependencePass": integrity_audit.get("group_independence_pass"),
                "legacyHeldOutStatus": integrity_audit.get("legacy_held_out", {}).get("final_evidence_status"),
                "replacement": integrity_audit.get("required_replacement"),
            },
        },
        "governance": {
            "methodFreeze": _read(FRAMEWORK / "emi" / "method_freeze.json", {}),
            "freshFinalSeal": fresh_seal,
            "freshFinalAccess": fresh_access,
            "freshFinalDecision": fresh_release,
        },
        "voiceValidation": {
            "sdkProbe": indus_live,
            "stressMatrix": voice_stress_validation,
            "stressLive": {"runtime": voice_stress_live, "metrics": voice_stress_metrics, "providerError": voice_provider_error},
            "adaptiveDuplex": adaptive_duplex_summary,
            "matchedHumanStatus": "adaptive_duplex_calibrated_pending_matched_baseline_candidate" if adaptive_valid_records else "pending_adaptive_duplex_and_matched_candidate",
        },
        "architecture": {
            "evaluationEngine": "Measures frozen versions; never mutates or promotes.",
            "improvementEngine": "Consumes development failures and produces versioned candidates.",
            "releaseController": "Re-evaluates candidates and applies exact per-case gates.",
        },
        "verification": verification,
        "claimBoundary": "Dynamic text evidence measures task, state and tool behavior; the static 200-case library is diagnostic only. Fresh-final and voice-transfer status are shown separately. No collected-payment or production-lift claim is made.",
    }
    write_json(path, snapshot)
    return snapshot["framework"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_DASHBOARD)
    args = parser.parse_args()
    print(json.dumps(export(args.output), indent=2))


if __name__ == "__main__":
    main()
