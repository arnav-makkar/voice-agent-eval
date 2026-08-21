"""Build a hash-linked execution manifest for stakeholder and interview review."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from framework.core.io import write_json


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "framework"
EMI = ARTIFACTS / "emi"
OUTPUT = ARTIFACTS / "execution_manifest.json"


def _read(path: Path, default: Any = None) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _sha(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def _ref(path: Path, data: Any = None) -> dict[str, Any]:
    return {
        "path": str(path),
        "sha256": _sha(path),
        "exists": path.exists(),
        **({"data": data if data is not None else _read(path, {})} if path.exists() else {}),
    }


def _dynamic(candidate: str) -> dict[str, Any]:
    root = EMI / "dynamic_experiments" / candidate
    raw = _read(root / "summary.json", {})
    rescored = _read(root / "rescore-v2" / "summary.json", {})
    semantic = _read(root / "semantic-v2" / "semantic_summary.json", {})
    aggregate = (rescored or raw).get("aggregate", {})
    return {
        "experiment_id": candidate,
        "raw_summary": _ref(root / "summary.json", raw),
        "deterministic_rescore": _ref(root / "rescore-v2" / "summary.json", rescored),
        "semantic_secondary": _ref(root / "semantic-v2" / "semantic_summary.json", semantic),
        "task_successes": aggregate.get("task_successes"),
        "records": aggregate.get("records"),
        "task_success_rate": aggregate.get("task_success_rate"),
        "experience": aggregate.get("average_experience_score"),
        "mlflow_run_id": raw.get("mlflow", {}).get("run_id"),
    }


def build(output: Path = OUTPUT) -> dict[str, Any]:
    selection_path = EMI / "selection.json"
    selection = _read(selection_path, {})
    freeze_path = EMI / "method_freeze.json"
    freeze = _read(freeze_path, {})
    dev_release_path = EMI / "dynamic_release_v15.json"
    gepa_release_path = EMI / "dynamic_release_gepa_finalist.json"
    final_release_path = EMI / "fresh_final_decision.json"
    final_release = _read(final_release_path, {})
    fresh_root = EMI / "dynamic_scenarios_v1"
    voice_root = EMI / "voice_stress_v1"
    voice_summary_path = voice_root / "live-v2" / "voice_summary.json"
    if not voice_summary_path.exists():
        voice_summary_path = voice_root / "live" / "voice_summary.json"
    verification_path = ARTIFACTS / "verification" / "latest.json"
    legacy_manifest = EMI / "datasets" / "emi_failure_derived_v3" / "manifest.json"
    legacy_integrity = EMI / "datasets" / "emi_failure_derived_v3" / "integrity_audit.json"

    record = {
        "schema_version": "framework-execution-manifest.v4",
        "generated_at": datetime.now(UTC).isoformat(),
        "framework_name": "Loopline",
        "framework_version": "1.0.0-interview-mvp",
        "validation_domain": "emi_recovery",
        "architecture": {
            "evaluation": "EVA-inspired stateful episodes with deterministic tool/state/guardrail truth plus a secondary semantic judge",
            "improvement": "failure routing across prompt, extractor, tool, workflow, knowledge, model, channel, and human-policy surfaces; manual and GEPA arms compete",
            "governance": "paired per-case regression gate, independent candidate selection, cryptographic method freeze, once-only group-separated final",
            "operations": "MLflow lineage, run IDs, immutable traces, first-failure localization, Loopline local dashboard",
        },
        "evidence_layers": {
            "real_voice_discovery": {
                "calls": 20,
                "role": "failure discovery and scenario design",
                "truth_status": "provisional_owner_review_required",
                "causal_or_gold_claim": False,
            },
            "legacy_static_library": {
                "manifest": _ref(legacy_manifest),
                "integrity_audit": _ref(legacy_integrity),
                "records": 200,
                "role": "development-only next-turn diagnostics",
                "final_evidence": False,
            },
            "stateful_development_suite": {
                "manifest": _ref(fresh_root / "manifest.json"),
                "records": 30,
                "splits": {"development": 18, "validation": 6, "regression": 6},
                "role": "candidate development, diagnosis, and paired regression gating",
            },
            "sealed_fresh_final": {
                "seal": _ref(fresh_root / "fresh_final_seal.json"),
                "access_log": _ref(fresh_root / "fresh_final_access_log.json"),
                "records": _read(fresh_root / "fresh_final_seal.json", {}).get("records"),
                "role": "once-only untouched final text-mode comparison",
            },
        },
        "development_experiments": {
            "baseline_v12": _dynamic("v12-dynamic-full"),
            "manual_v15": _dynamic("v15-firm-today-full"),
            "gepa_finalist": _dynamic("dynamic-gepa-finalist-full"),
            "gepa_lineage": _ref(EMI / "dynamic_gepa" / "lineage.json"),
            "manual_release_gate": _ref(dev_release_path),
            "gepa_release_gate": _ref(gepa_release_path),
        },
        "selection_and_freeze": {
            "selection": _ref(selection_path, selection),
            "method_freeze": _ref(freeze_path, freeze),
            "selected_candidate": selection.get("selected_candidate_id"),
            "method_bundle_sha256": freeze.get("method_bundle_sha256"),
        },
        "fresh_final_experiments": {
            "baseline_v12": _dynamic("v12-fresh-final"),
            "selected_v15": _dynamic("v15-fresh-final"),
            "paired_release": _ref(final_release_path, final_release),
        },
        "voice_component_evidence": {
            "stress_manifest": _ref(voice_root / "manifest.json"),
            "baseline_live_summary": _ref(voice_summary_path),
            "retry_provider_error": _ref(voice_root / "live-v2" / "provider_error.json"),
            "scope": "six baseline CALL-channel acoustic diagnostics; not a matched candidate voice A/B and not voice TSR",
        },
        "realtime_eva_evidence": {
            "latest_status": _ref(ROOT / "artifacts" / "eva_live" / "latest_status.json"),
            "valid_run": _ref(ROOT / "artifacts" / "eva_live" / "emi_eva_live_20260819_135630" / "attempt_status.json"),
            "scope": "one valid realtime ElevenLabs caller to deployed Samvaad V12 evaluation; not a reliability estimate or candidate comparison",
        },
        "prospective_evaluator": _ref(EMI / "eva_adapter_v11" / "evaluator_freeze.json"),
        "completion_audit": _ref(ARTIFACTS / "completion_audit.json"),
        "portability": _ref(ARTIFACTS / "hospital_appointments" / "summary.json"),
        "verification": _ref(verification_path),
        "remaining_human_or_external_gates": [
            "Owner semantic review of the 20 provisional real-call labels and confirmation that the previously exposed Sarvam key was rotated.",
            "A secure public tool route that the deployed Indus runtime can authenticate, followed by one captured live tool side effect.",
            "Commit the selected V15 prompt as an exact immutable Indus version, then run the frozen matched V12/V15 voice suite.",
            "Integrate a payment ledger or authenticated outcome join before claiming collected-cash lift.",
        ],
        "claim_boundary": (
            "This MVP demonstrates a reusable, executable self-improvement framework, text-mode task improvement under a sealed final protocol, "
            "and one valid realtime EVA-to-Samvaad evaluation. It does not yet prove production payment lift, a matched V15 voice improvement, "
            "live tool execution, or portability to a million-call corpus without domain contracts, sampling, calibration, and infrastructure changes."
        ),
    }
    write_json(output, record)
    return record


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
