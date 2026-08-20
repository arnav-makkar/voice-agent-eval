"""Single CLI entry point for framework status and safe stage execution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from framework.datasets.domain_smoke import build as build_domain_smoke
from framework.datasets.audit_integrity import audit as audit_integrity
from framework.datasets.migrate_outcomes_v3 import migrate as migrate_outcomes
from framework.datasets.repair_v3_anchors import repair as repair_anchors
from framework.diagnosis.router import build as build_diagnosis
from framework.evaluators.calibrate import calibrate
from framework.export_dashboard import export as export_dashboard
from framework.ingestion.canonicalize import canonicalize
from framework.report import build as build_report


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "framework"


def _read(path: Path, default: Any = None) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def status() -> dict[str, Any]:
    dataset = ARTIFACTS / "emi" / "datasets" / "emi_failure_derived_v3"
    validation = _read(dataset / "validation.json", {})
    manifest = _read(dataset / "manifest.json", {})
    integrity_audit = _read(dataset / "integrity_audit.json", {})
    calibration_summary = _read(ARTIFACTS / "emi" / "evaluator_calibration" / "summary.json", {})
    diagnosis_summary = _read(ARTIFACTS / "emi" / "diagnosis" / "summary.json", {})
    gepa_lineage = _read(ARTIFACTS / "emi" / "gepa" / "lineage.json", {})
    gepa_deployable = _read(ARTIFACTS / "emi" / "gepa" / "deployable-finalist.json", {})
    experiments = [
        path for path in (ARTIFACTS / "emi" / "experiments").glob("*/summary.json")
        if _read(path, {}).get("dataset_id") == "emi_failure_derived_v3"
    ]
    release = _read(ARTIFACTS / "emi" / "release" / "decision.json", {})
    dynamic_root = ARTIFACTS / "emi" / "dynamic_experiments"
    baseline_dynamic = _read(dynamic_root / "v12-dynamic-full" / "rescore-v2" / "summary.json", {})
    v15_dynamic = _read(dynamic_root / "v15-firm-today-full" / "rescore-v2" / "summary.json", {})
    gepa_dynamic = _read(dynamic_root / "dynamic-gepa-finalist-full" / "rescore-v2" / "summary.json", {})
    dynamic_selection = _read(ARTIFACTS / "emi" / "selection.json", {})
    dynamic_release = _read(ARTIFACTS / "emi" / "dynamic_release_v15.json", {})
    gepa_dynamic_release = _read(ARTIFACTS / "emi" / "dynamic_release_gepa_finalist.json", {})
    method_freeze = _read(ARTIFACTS / "emi" / "method_freeze.json", {})
    fresh_seal = _read(ARTIFACTS / "emi" / "dynamic_scenarios_v1" / "fresh_final_seal.json", {})
    fresh_access = _read(ARTIFACTS / "emi" / "dynamic_scenarios_v1" / "fresh_final_access_log.json", {})
    fresh_baseline = _read(dynamic_root / "v12-fresh-final" / "summary.json", {})
    fresh_candidate = _read(dynamic_root / "v15-fresh-final" / "summary.json", {})
    fresh_decision = _read(ARTIFACTS / "emi" / "fresh_final_decision.json", {})
    voice_root = ARTIFACTS / "emi" / "voice_stress_v1"
    voice_summary = _read(voice_root / "live-v2" / "voice_summary.json", {}) or _read(voice_root / "live" / "voice_summary.json", {})
    voice_provider_error = _read(voice_root / "live-v2" / "provider_error.json", {})
    return {
        "schema_version": "framework-status.v1",
        "stages": {
            "canonical_traces": {"status": "complete" if (ARTIFACTS / "emi" / "traces.jsonl").exists() else "missing", "records": 20},
            "reference_annotations": {"status": "human_review_required", "records": 20, "truth_status": "provisional"},
            "failure_dataset": {
                "status": "static_development_library" if validation.get("status") == "pass" else "missing",
                "dataset_id": manifest.get("metadata", {}).get("dataset_id"),
                "records": validation.get("total"),
                "evidence_type": "static_next_turn_cases",
                "group_independence_pass": integrity_audit.get("group_independence_pass"),
                "legacy_held_out_status": integrity_audit.get("legacy_held_out", {}).get("final_evidence_status"),
            },
            "evaluator": {
                "status": "stateful_primary_plus_semantic_secondary" if baseline_dynamic else "limited",
                "agreement": calibration_summary.get("agreement", {}),
                "reason": "deterministic tool/state/guardrail checks are primary; the Gemini Pro semantic judge is advisory",
            },
            "diagnosis": {
                "status": "available" if diagnosis_summary.get("episodes") else "missing",
                "failure_episodes": diagnosis_summary.get("episodes", 0),
                "review_status": diagnosis_summary.get("review_status"),
            },
            "extractor": {"status": "candidate_complete", "deployment_status": "not_deployed"},
            "offline_experiments": {"status": "running" if not experiments else "available", "valid_v3_runs": len(experiments)},
            "dynamic_evaluation": {
                "status": "complete" if baseline_dynamic and v15_dynamic and gepa_dynamic else "incomplete",
                "scenarios": baseline_dynamic.get("aggregate", {}).get("records"),
                "baseline_successes": baseline_dynamic.get("aggregate", {}).get("task_successes"),
                "manual_repair_successes": v15_dynamic.get("aggregate", {}).get("task_successes"),
                "gepa_successes": gepa_dynamic.get("aggregate", {}).get("task_successes"),
            },
            "gepa": {
                "status": "stateful_arm_complete" if gepa_dynamic else "legacy_static_only",
                "candidate_count": _read(ARTIFACTS / "emi" / "dynamic_gepa" / "lineage.json", {}).get("engine_candidate_count"),
                "task_successes": gepa_dynamic.get("aggregate", {}).get("task_successes"),
                "release_decision": gepa_dynamic_release.get("decision"),
                "legacy_static_candidate": gepa_deployable.get("candidate_id"),
            },
            "legacy_static_release_gate": {
                "status": release.get("decision", "not_run"),
                "new_severe_regressions": release.get("new_severe_regression_count"),
                "claim_boundary": release.get("claim_boundary"),
            },
            "candidate_selection": {
                "status": "complete" if dynamic_selection else "not_run",
                "selected_candidate_id": dynamic_selection.get("selected_candidate_id"),
                "development_gate": dynamic_release.get("decision"),
            },
            "method_freeze": {
                "status": "complete" if method_freeze else "not_run",
                "method_bundle_sha256": method_freeze.get("method_bundle_sha256"),
            },
            "fresh_group_separated_final_test": {
                "status": "complete" if fresh_baseline and fresh_candidate else ("sealed" if fresh_seal else "not_built"),
                "records": fresh_seal.get("records"),
                "baseline_successes": fresh_baseline.get("aggregate", {}).get("task_successes"),
                "candidate_successes": fresh_candidate.get("aggregate", {}).get("task_successes"),
                "decision": fresh_decision.get("decision"),
                "evaluation_runs": len(fresh_access.get("evaluation_runs", [])),
                "owner_semantic_review": fresh_seal.get("review_status"),
            },
            "matched_voice": {
                "status": "baseline_component_diagnostic_complete_candidate_match_blocked" if voice_summary and voice_provider_error else ("baseline_component_diagnostic_complete" if voice_summary else "not_run"),
                "conditions": voice_summary.get("records") or voice_summary.get("condition_count"),
                "provider_error": voice_provider_error.get("message"),
                "claim_boundary": "Baseline Indus acoustic diagnostics only; no matched v15 voice A/B or voice TSR claim.",
            },
            "business_outcome": {"status": "unobservable", "proxy": "explicit verbal pay-now commitment"},
        },
        "hard_blockers": [
            "Owner review of the 20 provisional discovery annotations and sealed final-card semantics before any production decision.",
            "A matched v15 Indus voice A/B requires an approved prompt commit and replenished provider credits; the current retry returned HTTP 402.",
            "Actual payment settlement remains unobservable without a ledger/tool integration.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["status", "canonicalize", "migrate-v3", "repair-anchors", "audit-integrity", "diagnose", "calibrate", "domain-smoke", "export-dashboard", "report"])
    args = parser.parse_args()
    if args.command == "status":
        result = status()
    elif args.command == "canonicalize":
        result = canonicalize()
    elif args.command == "migrate-v3":
        result = migrate_outcomes()
    elif args.command == "repair-anchors":
        result = repair_anchors()
    elif args.command == "audit-integrity":
        result = audit_integrity()
    elif args.command == "diagnose":
        result = build_diagnosis()
    elif args.command == "calibrate":
        result = calibrate()
    elif args.command == "domain-smoke":
        result = build_domain_smoke()
    elif args.command == "export-dashboard":
        result = export_dashboard()
    else:
        result = build_report()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
