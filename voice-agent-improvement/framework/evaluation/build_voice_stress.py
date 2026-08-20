"""Build a paired acoustic-condition matrix for the live Indus CALL adapter."""

from __future__ import annotations

import json
from pathlib import Path

from framework.core.io import manifest, write_json, write_jsonl
from framework.evaluation.build_emi_scenarios import COMMON_FORBIDDEN, _context, _initial
from framework.evaluation.contracts import EvaluationScenario, UserStep


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "artifacts" / "framework" / "emi" / "voice_stress_v1"

CONDITIONS = [
    ("clean", ["clean"]),
    ("fast", ["fast_speech_1_25x"]),
    ("noise", ["background_noise_12db"]),
    ("quiet", ["low_volume_12db"]),
    ("packet_loss", ["packet_loss_5pct"]),
    ("fast_noise", ["fast_speech_1_25x", "background_noise_12db"]),
]


def build(output: Path = OUTPUT) -> dict:
    context = _context(41)
    scenarios = []
    for index, (label, perturbations) in enumerate(CONDITIONS, start=1):
        scenarios.append(
            EvaluationScenario(
                schema_version="evaluation-scenario.v1",
                scenario_id=f"EMI-VOICE-{index:03d}",
                domain_id="emi_recovery",
                split="regression",
                source_group="paired-acoustic-pay-now-v1",
                failure_family="acoustic_pay_now_transfer",
                language="hinglish",
                user_goal="Acknowledge identity and make an explicit pay-now commitment",
                persona={"patience": "low", "engagement": "uninterested", "verbosity": "terse"},
                visible_context=context,
                hidden_state={"target_disposition": "payment_ready", "acoustic_condition": label},
                initial_environment=_initial(context),
                user_steps=[
                    UserStep("haan boliye", "identity_ack"),
                    UserStep("theek hai, main abhi EasyCredit app khol ke payment karta hoon", "explicit_pay_now"),
                ],
                accepted_dispositions=["payment_ready"],
                expected_state={"disposition": "payment_ready"},
                forbidden_phrases=COMMON_FORBIDDEN,
                perturbations=perturbations,
                max_agent_turns=4,
                reviewer_status="authored_and_code_reviewed",
            )
        )
    artifact = write_jsonl(output / "scenarios.jsonl", [item.to_record() for item in scenarios])
    validation = {
        "schema_version": "voice-stress-validation.v1",
        "records": len(scenarios),
        "paired_semantic_script": True,
        "conditions": [label for label, _ in CONDITIONS],
        "claim_boundary": "Deterministic local signal stress on one synthetic macOS caller voice; not a population or human-acoustic benchmark.",
    }
    validation_artifact = write_json(output / "validation.json", validation)
    result = manifest(
        "voice_stress_matrix",
        [artifact, validation_artifact],
        dataset_id="emi_voice_stress_v1",
        schema="evaluation-scenario.v1",
        records=len(scenarios),
        source="project_owned_paired_acoustic_conditions_inspired_by_tau_voice",
    )
    write_json(output / "manifest.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
