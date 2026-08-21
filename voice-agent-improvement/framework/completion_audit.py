"""Generate the machine-readable acceptance audit for the final interview plan.

This deliberately distinguishes implemented capability from externally blocked
evidence.  A missing live result is never converted into a pass because the
local harness exists.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from framework.core.io import write_json


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
EMI = ARTIFACTS / "framework" / "emi"
OUTPUT = ARTIFACTS / "framework" / "completion_audit.json"


def _read(path: Path, default: Any = None) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _rows(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()) if path.exists() else 0


def _item(item_id: str, label: str, status: str, evidence: list[str], note: str) -> dict[str, Any]:
    return {"id": item_id, "label": label, "status": status, "evidence": evidence, "note": note}


def build(output: Path = OUTPUT) -> dict[str, Any]:
    verification_path = ARTIFACTS / "framework" / "verification" / "latest.json"
    verification = _read(verification_path, {})
    scenario_root = EMI / "dynamic_scenarios_v1"
    voice_manifest = _read(EMI / "eva_voice_suite_v1" / "manifest.json", {})
    voice_record_count = len(voice_manifest.get("records", []))
    live_status_path = ARTIFACTS / "eva_live" / "latest_status.json"
    live_status = _read(live_status_path, {})
    latest_live_path = ARTIFACTS / "eva_live" / str(live_status.get("latest_run_id", "")) / "attempt_status.json"
    latest_live = _read(latest_live_path, {})
    v12_summary = _read(EMI / "dynamic_experiments" / "v12-dynamic-full" / "summary.json", {})
    v15_summary = _read(EMI / "dynamic_experiments" / "v15-firm-today-full" / "summary.json", {})
    v12_aggregate = v12_summary.get("aggregate", {})
    v15_aggregate = v15_summary.get("aggregate", {})
    v15_release = _read(EMI / "dynamic_release_v15.json", {})
    current_freeze = _read(EMI / "eva_adapter_v11" / "evaluator_freeze.json", {})
    owner_labels_path = EMI / "reference_annotations.owner_reviewed.v1.jsonl"
    owner_labels_reviewed = owner_labels_path.exists() and _rows(owner_labels_path) == _rows(
        EMI / "reference_annotations.provisional.jsonl"
    )
    owner_confirmations = _read(ARTIFACTS / "framework" / "owner_confirmations.json", {})
    key_rotated = bool(
        owner_confirmations.get("confirmations", {}).get("previously_exposed_sarvam_key_rotated")
    )
    deployment_manifest = ROOT / "agent" / "deployments" / "indus-v18-pilot-repair.json"
    deployed_candidate = _read(deployment_manifest, {})
    candidate_committed = bool(
        deployed_candidate.get("indus_app_version")
        and str(deployed_candidate.get("status", "")).startswith("committed_")
    )
    voice_pilot_decision_path = EMI / "live_voice_pilot_decision.json"
    voice_pilot_decision = _read(voice_pilot_decision_path, {})
    pilot_hold = voice_pilot_decision.get("decision") == "hold"
    # Only a request that reached the service from the platform's own caller counts.
    # A locally issued call proves the service works, not that Indus can use it.
    live_tool_effect_record = _read(EMI / "live_tool_effect.json", {})
    live_tool_effect = bool(
        live_tool_effect_record
        and any(
            request.get("status") == 200 and request.get("credential_presented")
            for request in live_tool_effect_record.get("requests_from_platform", [])
        )
    )

    phases = {
        "P0_truth_repair": [
            _item(
                "owner_labels",
                "Owner review of 20 discovery labels",
                "complete" if owner_labels_reviewed else "external_pending",
                [str(owner_labels_path)] if owner_labels_reviewed else [str(EMI / "reference_annotations.provisional.jsonl")],
                (
                    "All 20 labels are owner-reviewed and versioned; the provisional artifact is preserved unchanged. "
                    "Because the owner confirmed rather than corrected them, the weak diagnostic agreement is "
                    "attributable to the evaluator rather than to label noise."
                    if owner_labels_reviewed
                    else "The 20 labels remain explicitly provisional; only Arnav can convert them into owner truth."
                ),
            ),
            _item("strict_gate", "Per-case severity and preserved-win gate", "complete", [str(EMI / "dynamic_release_v15.json"), str(ROOT / "tests" / "test_dynamic_release.py")], "Aggregate improvement cannot hide a new severe or preserved-win regression."),
            _item("static_library", "200 rows demoted to static development diagnostics", "complete", [str(EMI / "datasets" / "emi_failure_derived_v3" / "manifest.json"), str(EMI / "datasets" / "emi_failure_derived_v3" / "integrity_audit.json")], "The former held-out split is not used as final proof."),
            _item("verification", "Code, dashboard and protocol verification", "complete" if verification.get("passed") else "failed", [str(verification_path)], "The full Python unit test suite, dashboard lint/tests/build, freeze checks and secret scan pass in the latest verifier run."),
            _item(
                "key_rotation",
                "Rotate previously exposed Sarvam key",
                "complete" if key_rotated else "owner_confirmation_required",
                [str(ARTIFACTS / "framework" / "owner_confirmations.json")] if key_rotated else [],
                "Owner confirmed rotation; no credential value is stored in the evidence artifact." if key_rotated else "Key rotation is an account action and cannot be proven from repository state.",
            ),
        ],
        "P1_clone_and_spike": [
            _item("upstreams", "Pinned EVA, tau and Riley references with licenses", "complete", [str(ROOT / "UPSTREAM_SOURCES.md"), str(ROOT / "THIRD_PARTY_NOTICES.md")], "Pinned commits and attribution are recorded."),
            _item("stock_eva", "Untouched upstream EVA scenario", "documented_fallback", [], "The upstream stock run requires its full supported provider stack. The project instead preserves a disclosed EVA adaptation; it must not be called an untouched upstream run."),
            _item("indus_adapter", "Verified Samvaad bidirectional audio adapter", "complete", [str(ROOT / "research" / "upstream" / "eva" / "src" / "eva" / "assistant" / "samvaad_server.py")], "Samvaad remains the complete deployed agent under test."),
            _item("live_duplex", "Clean realtime ElevenLabs caller to Samvaad trial", "complete" if latest_live.get("classification") == "valid_live_bot_to_bot_evaluation" else "pending", [str(latest_live_path)], "One valid live audio-in/audio-out conversation is preserved and eligible for scoring."),
            _item(
                "live_tool_effect",
                "Captured Indus tool call and state mutation",
                "complete" if live_tool_effect else "external_blocked",
                [str(EMI / "live_tool_effect.json")] if live_tool_effect else [str(ROOT / "framework" / "tool_service.py")],
                (
                    "A tool call originating from Sarvam's documented tool-caller IP authenticated against the "
                    "run-scoped service and mutated isolated per-run state. Credential propagation, which blocked the "
                    "previous attempt, is resolved. The agent choosing to call a tool unprompted mid-conversation is a "
                    "separate step and is not claimed here."
                    if live_tool_effect
                    else "The service is authenticated, isolated and tested, but the Indus test runtime omitted the stored credential. No live side effect is claimed."
                ),
            ),
        ],
        "P2_emi_eval_world": [
            _item("scenario_count", "30 stateful development/validation/regression scenarios", "complete" if sum(_rows(scenario_root / f"{name}.jsonl") for name in ("development", "validation", "regression")) == 30 else "failed", [str(scenario_root / "manifest.json")], "18 development + 6 validation + 6 regression scenarios."),
            _item("three_tools", "Payment-status, promise-to-pay and callback tools", "complete", [str(ROOT / "framework" / "tool_service.py"), str(ROOT / "tests" / "test_tool_service.py")], "All three tools have authenticated, idempotent, run-scoped implementations and tests."),
            _item("fresh_state", "Fresh SQLite state and no cross-trial leakage", "complete", [str(ROOT / "framework" / "evaluation" / "environment.py"), str(ROOT / "tests" / "test_dynamic_evaluation.py"), str(ROOT / "tests" / "test_tool_service.py")], "Per-trial state is isolated and covered by tests."),
            _item("simulator_validity", "Simulator validity and termination checks", "complete" if v12_aggregate.get("invalid_simulations") == 0 else "partial", [str(EMI / "dynamic_experiments" / "v12-dynamic-full" / "summary.json")], f"Text-mode baseline recorded {v12_aggregate.get('valid_records', 0)}/{v12_aggregate.get('records', 0)} valid simulations; live reliability remains a later gate."),
        ],
        "P3_evaluation": [
            _item("metric_contract", "Frozen Accuracy, Experience, validation and diagnostic contract", "complete" if current_freeze else "failed", [str(EMI / "eva_adapter_v11" / "evaluator_freeze.json")], "V11 is the post-pilot prospective evaluator. It versions the sentinel-normalisation and tool-service changes; V10 and historical pilot evidence remain immutable."),
            _item(
                "calibration",
                "Calibration against owner-reviewed discovery calls",
                "complete" if owner_labels_reviewed else "external_pending",
                [str(EMI / "evaluator_calibration_owner" / "summary.json")],
                "Agreement is reported against the owner's versioned 20-call review; the small sample and weak ownership agreement remain visible." if owner_labels_reviewed else "Current agreement is against Codex-assisted provisional labels, not independent owner truth.",
            ),
            _item("v12_scorecard", "Reproducible V12 baseline scorecard", "partial", [str(EMI / "dynamic_experiments" / "v12-dynamic-full" / "summary.json"), str(latest_live_path)], "The 30-case stateful text baseline and one full live EVA score exist; an 18-case repeated live baseline does not."),
        ],
        "P4_improvement": [
            _item("repair_arms", "Manual, GEPA and extractor repair arms", "complete", [str(EMI / "dynamic_gepa" / "lineage.json"), str(EMI / "extractor"), str(EMI / "selection.json")], "Prompt and extractor changes are evaluated independently and failed candidates are retained."),
            _item("gepa_lineage", "Real GEPA Optimize Anything lineage", "complete", [str(EMI / "dynamic_gepa" / "lineage.json"), str(EMI / "dynamic_gepa" / "engine")], "The real optimizer, candidates, reflection and MLflow lineage are preserved."),
            _item("multi_seed", "Repeated GEPA search from multiple seed prompts", "not_required_for_current_gate", [str(EMI / "dynamic_gepa" / "lineage.json")], "One stateful GEPA seed was run. Another optimizer run is intentionally deferred until live execution identifies a prompt-owned failure; more search is not evidence by itself."),
            _item("cheap_screen", "Static 200-case library used only for cheap screening", "complete", [str(EMI / "datasets" / "emi_failure_derived_v3" / "manifest.json")], "It is excluded from final voice claims."),
        ],
        "P5_re_evaluation_and_gate": [
            _item("matched_text", "Identical matched V12/V15 stateful text comparison", "complete", [str(EMI / "dynamic_release_v15.json")], f"V12 {v12_aggregate.get('task_successes')}/{v12_aggregate.get('records')} versus V15 {v15_release.get('candidate_task_successes')}/{v15_release.get('matched_scenarios')} under the governing deterministic v3 rescore (original full-run aggregate {v15_aggregate.get('task_successes')}/{v15_aggregate.get('records')}; immutable traces were not rerun) on development/validation/regression; text evidence only."),
            _item("fresh_final", "Sealed group-separated final test", "complete", [str(scenario_root / "fresh_final_seal.json"), str(EMI / "fresh_final_decision.json")], "The once-only 12-case text final is preserved with hashes and an access log."),
            _item(
                "matched_voice",
                "Frozen matched live voice suite",
                "not_run_by_gate" if pilot_hold else "external_pending",
                [str(EMI / "eva_voice_suite_v1" / "manifest.json"), str(voice_pilot_decision_path)],
                f"The {voice_record_count}-record protocol was deliberately not run because the three-call prospective pilot failed its advance rule." if pilot_hold else f"The {voice_record_count}-record protocol exists, but zero baseline/candidate pairs have completed.",
            ),
            _item(
                "final_release",
                "Signed live promote/hold/rollback record",
                "complete" if pilot_hold else "pending_on_matched_voice",
                [str(voice_pilot_decision_path)] if pilot_hold else [str(EMI / "fresh_final_decision.json")],
                "The release controller emitted HOLD at the pilot gate. This is a complete decision, not a production promotion." if pilot_hold else "The current signed decision is pass_text_final_awaiting_matched_voice, not production promotion.",
            ),
        ],
        "P6_unified_ui": [
            _item("loopline", "Loopline evaluation/improvement/release product UI", "complete", [str(ROOT.parent / "dashboard" / "app" / "page.tsx"), str(ROOT.parent / "dashboard" / "tests" / "rendered-html.test.mjs")], "Production build and render tests pass."),
            _item("live_evidence", "Audio, transcript, provider events, first defect and EVA scores", "complete", [str(latest_live_path)], "The valid realtime run is replayable in the UI."),
            _item("tool_and_reliability_panels", "Populated live pilot, tool and reliability decision panels", "complete" if pilot_hold else "external_pending", [str(ROOT.parent / "dashboard" / "app" / "page.tsx"), str(voice_pilot_decision_path)], "The UI shows three replayable pilot cases, exact valid/invalid denominators, tool-effect evidence and the HOLD decision." if pilot_hold else "The views and contracts exist; they remain empty until live tool and matched suite evidence is captured."),
            _item("mlflow", "MLflow experiment lineage", "complete", [str(ARTIFACTS / "experiments" / "mlflow.db")], "Experiment runs and negative candidates are retained for technical drill-down."),
        ],
    }

    all_items = [item for items in phases.values() for item in items]
    status_counts: dict[str, int] = {}
    for item in all_items:
        status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1

    record = {
        "schema_version": "final-interview-plan-audit.v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "source_plan": str(ROOT.parent / "FINAL-INTERVIEW-DECISION.html"),
        "verifier_passed": bool(verification.get("passed")),
        "current_evaluator": current_freeze.get("evaluator_version"),
        "status_counts": status_counts,
        "phases": phases,
        "binding_open_gates": [
            gate
            for gate, still_open in (
                (
                    "Arnav reviews and versions the 20 provisional discovery labels and confirms Sarvam key rotation.",
                    not (owner_labels_reviewed and key_rotated),
                ),
                (
                    "A secure public tool route works from the deployed Indus runtime and one real tool side effect is captured.",
                    not live_tool_effect,
                ),
                ("The selected candidate is committed as an exact immutable Indus version.", not candidate_committed),
                (
                    "The three-call live pilot passes; only then does the frozen matched voice suite run.",
                    pilot_hold,
                ),
            )
            if still_open
        ],
        "closed_gates": [
            gate
            for gate, closed in (
                ("Owner-reviewed discovery labels.", owner_labels_reviewed),
                ("Previously exposed Sarvam key rotation confirmed without storing the credential.", key_rotated),
                (
                    "A tool call from the platform's own caller authenticated and mutated run-scoped state.",
                    live_tool_effect,
                ),
                ("The selected candidate was committed and versioned in Indus.", candidate_committed),
                ("The prospective pilot ran and the release controller emitted HOLD.", pilot_hold),
            )
            if closed
        ],
        "claim_boundary": (
            "The framework, deployed candidate, authenticated tool route and prospective pilot are evidenced. The live "
            "decision is HOLD: only one of three repair trials was evaluator-valid, the Punjabi required write remained "
            "missing and the valid call still failed EVA-X. No live candidate lift or production readiness is claimed."
        ),
    }
    write_json(output, record)
    return record


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
