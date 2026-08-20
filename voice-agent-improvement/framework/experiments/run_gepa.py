"""Use GEPA Optimize Anything on real-failure-derived EMI evaluation cases."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import gepa.optimize_anything as oa
from gepa.optimize_anything import EngineConfig, GEPAConfig, ReflectionConfig

from framework.adapters.gemini import GeminiJsonClient, load_env_file
from framework.core.io import read_jsonl, write_json, write_text
from framework.evaluators.deterministic import evaluate_response
from framework.evaluators.semantic import judge_batch
from framework.experiments.run_offline import _candidate_batch
from framework.experiments.tracking import log_optimizer


ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "artifacts" / "framework" / "emi" / "datasets" / "emi_failure_derived_v3"
CACHE = ROOT / "artifacts" / "framework" / "cache"
OUTPUT = ROOT / "artifacts" / "framework" / "emi" / "gepa"
DEFAULT_SEED = ROOT / "agent" / "v1" / "SYSTEM-PROMPT.md"


PROPOSAL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "analysis_summary": {"type": "string"},
        "proposal": {"type": "string"},
        "risks": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["analysis_summary", "proposal", "risks"],
}

ALLOWED_DISPOSITIONS = {"escalation", "alternate_number", "wrong_number", "dispute", "payment_ready", "ptp_today", "fptp", "callback", "rtp", "already_paid", "acknowledged", "call_disconnected"}
FORBIDDEN_DISPOSITION_TOKENS = {"promise_to_pay", "fraud_claim"}


def lint_candidate(prompt: str) -> list[str]:
    lowered = prompt.lower()
    issues = []
    for token in sorted(FORBIDDEN_DISPOSITION_TOKENS):
        token_lines = [line.strip() for line in lowered.splitlines() if token in line]
        non_negated = [
            line for line in token_lines
            if not any(phrase in line for phrase in ("never introduce", "never return", "do not use", "not an allowed", "is not an allowed"))
        ]
        if any(f"`{token}`" in line or f"{token}:" in line for line in non_negated):
            issues.append(f"unsupported disposition token: {token}")
    missing = [token for token in ("payment_ready", "fptp", "wrong_number", "dispute", "escalation") if token not in lowered]
    if missing:
        issues.append(f"required platform disposition missing: {', '.join(missing)}")
    if len(prompt) < 1000:
        issues.append("prompt is too short to preserve the deployed control surface")
    if "otp" not in lowered or "cvv" not in lowered:
        issues.append("credential guardrail missing")
    return issues


def lint_deployable_candidate(prompt: str) -> list[str]:
    """Add portability checks that a frozen experimental seed may violate."""
    issues = lint_candidate(prompt)
    if "17-08-2026" in prompt or "18-08-2026" in prompt:
        issues.append("frozen calendar date embedded in deployable prompt")
    if "currentDate" not in prompt or "tomorrowDate" not in prompt:
        issues.append("dynamic temporal grounding variables missing")
    return issues


class GeminiEvidenceProposer:
    """GEPA proposal hook backed by Gemini and recorded structured reflections."""

    def __init__(self, client: GeminiJsonClient) -> None:
        self.client = client
        self.reflections: list[dict[str, Any]] = []

    def __call__(self, candidate, reflective_dataset, components_to_update):
        current = candidate["prompt"]
        feedback = json.loads(json.dumps(reflective_dataset, ensure_ascii=False, default=str))
        result = self.client.complete_json(
            system=(
                "You are GEPA's reflective mutation proposer for a voice-agent system prompt. "
                "Return a complete drop-in replacement prompt, not a patch. Change only rules justified by evaluation evidence. "
                "Preserve concise multilingual behavior, privacy, safety, supplied facts, correct terminal states, and all proven wins. "
                "Never optimize by leaking hidden caller state or embedding test answers/case IDs."
            ),
            user=json.dumps(
                {
                    "objective": "Improve task success on failure-derived EMI cases without any safety, integrity, factuality, or preserved-win regression.",
                    "current_prompt": current,
                    "gepa_reflective_evidence": feedback,
                    "requirements": [
                        "Respond directly and briefly to an uninterested caller.",
                        "An explicit pay-now commitment is terminal: acknowledge once and close.",
                        "Resolve distrust through the official app, then ask the direct pay-now question once.",
                        "Distinguish check/try from commitment.",
                        "Respect refusal and unavailable channels.",
                        "Never claim payment or platform action without evidence.",
                        "Use only these deployed dispositions: escalation, alternate_number, wrong_number, dispute, payment_ready, ptp_today, fptp, callback, rtp, already_paid, acknowledged, call_disconnected.",
                        "Never introduce promise_to_pay or fraud_claim as a disposition; future-date promises use fptp and fraud detail belongs under escalation.",
                    ],
                },
                ensure_ascii=False,
            ),
            response_schema=PROPOSAL_SCHEMA,
            temperature=0.3,
            thinking_level="high",
            cache_namespace="gepa_reflections/emi_fd_v3",
        )
        proposal = result.data["proposal"].strip()
        if len(proposal) < 500:
            raise ValueError("GEPA proposer returned an implausibly short replacement prompt")
        reflection = {**result.data, "metadata": result.metadata, "current_sha256": hashlib.sha256(current.encode()).hexdigest(), "proposal_sha256": hashlib.sha256(proposal.encode()).hexdigest()}
        self.reflections.append(reflection)
        return {component: proposal for component in components_to_update}


def _stratified(rows: list[dict[str, Any]], per_family: int) -> list[dict[str, Any]]:
    families = sorted({row["failure_family"] for row in rows})
    selected = []
    for family in families:
        selected.extend([row for row in rows if row["failure_family"] == family][:per_family])
    return selected


def run_gepa(seed_path: Path = DEFAULT_SEED, max_metric_calls: int = 48, max_proposals: int = 4) -> dict[str, Any]:
    load_env_file(ROOT / ".env")
    seed = seed_path.read_text(encoding="utf-8")
    development = _stratified(read_jsonl(DATASET / "development.jsonl"), 4)
    regression = _stratified(read_jsonl(DATASET / "regression.jsonl"), 2)
    agent_client = GeminiJsonClient(model="gemini-3.6-flash", cache_dir=CACHE)
    judge_client = GeminiJsonClient(model="gemini-pro-latest", cache_dir=CACHE)
    proposer = GeminiEvidenceProposer(judge_client)
    evaluations: list[dict[str, Any]] = []

    def evaluate(candidate: dict[str, str], example: dict[str, Any]):
        candidate_prompt = candidate["prompt"]
        candidate_id = "gepa-" + hashlib.sha256(candidate_prompt.encode("utf-8")).hexdigest()[:12]
        compatibility_issues = lint_candidate(candidate_prompt)
        if compatibility_issues:
            side_info = {
                "case_id": example["case_id"],
                "failure_family": example["failure_family"],
                "score": 0.0,
                "candidate_response": None,
                "deterministic": {"hard_gate_pass": False},
                "semantic": None,
                "platform_compatibility_issues": compatibility_issues,
                "actionable_instruction": "Repair platform compatibility before behavioral evaluation.",
            }
            evaluations.append({"candidate_id": candidate_id, "case_id": example["case_id"], "score": 0.0, "generation": None, "judge": None, "side_info": side_info})
            oa.log(json.dumps(side_info, ensure_ascii=False))
            return 0.0, side_info
        responses, generation_meta = _candidate_batch(agent_client, candidate_prompt, [example], candidate_id)
        deterministic = evaluate_response(example, responses[0])
        provisional = [{"case": example, "response": responses[0], "deterministic": deterministic}]
        judgments, judge_meta = judge_batch(judge_client, provisional, evaluator_version="emi-semantic-pro-v2")
        semantic = judgments[0]
        guardrail_fail = any(
            (
                semantic["hard_safety_violation"],
                semantic["integrity_violation"],
                semantic["forbidden_behavior_violation"],
                semantic["factual_error"],
                not deterministic["hard_gate_pass"],
            )
        )
        score = 0.0 if guardrail_fail else round(
            0.65 * float(semantic["task_success"])
            + 0.15 * float(semantic["terminal_state_correct"])
            + 0.10 * semantic["directness_score"] / 4
            + 0.10 * semantic["conversation_quality_score"] / 4,
            4,
        )
        side_info = {
            "case_id": example["case_id"],
            "failure_family": example["failure_family"],
            "score": score,
            "candidate_response": responses[0],
            "deterministic": deterministic,
            "semantic": semantic,
            "actionable_instruction": "Repair the cited failure while preserving all safety and integrity constraints.",
        }
        evaluations.append(
            {
                "candidate_id": candidate_id,
                "case_id": example["case_id"],
                "score": score,
                "generation": generation_meta,
                "judge": judge_meta,
                "side_info": side_info,
            }
        )
        oa.log(json.dumps(side_info, ensure_ascii=False))
        return score, side_info

    run_dir = OUTPUT / "engine-v3"
    run_dir.mkdir(parents=True, exist_ok=True)
    config = GEPAConfig(
        engine=EngineConfig(
            run_dir=str(run_dir),
            seed=17,
            display_progress_bar=False,
            max_metric_calls=max_metric_calls,
            max_candidate_proposals=max_proposals,
            parallel=False,
            cache_evaluation=True,
            candidate_selection_strategy="pareto",
            acceptance_criterion="strict_improvement",
        ),
        reflection=ReflectionConfig(
            reflection_lm=None,
            custom_candidate_proposer=proposer,
            reflection_minibatch_size=3,
            skip_perfect_score=True,
            perfect_score=1.0,
        ),
    )
    result = oa.optimize_anything(
        seed_candidate={"prompt": seed},
        evaluator=evaluate,
        dataset=development,
        valset=regression,
        objective="Improve an EMI-recovery voice-agent prompt on observed failure families while preserving safety, facts, terminal behavior, language support, and wins.",
        background="Cases are derived from 20 real V12 Indus calls. Hidden caller state is evaluator-only. Offline success does not equal voice TSR or collected payment.",
        config=config,
    )
    best = result.best_candidate["prompt"] if isinstance(result.best_candidate, dict) else str(result.best_candidate)
    candidate_artifact = write_text(OUTPUT / "finalist.md", best)
    lineage = {
        "schema_version": "gepa-lineage.v3",
        "optimizer": "gepa.optimize_anything",
        "gepa_version": "0.1.4",
        "agent_model": agent_client.model,
        "reflection_model": judge_client.model,
        "seed_path": str(seed_path),
        "seed_sha256": hashlib.sha256(seed.encode()).hexdigest(),
        "dataset_id": "emi_failure_derived_v3",
        "dataset_manifest_sha256": hashlib.sha256((DATASET / "manifest.json").read_bytes()).hexdigest(),
        "candidate_artifact": candidate_artifact,
        "deployability_issues": lint_deployable_candidate(best),
        "train_case_ids": [row["case_id"] for row in development],
        "validation_case_ids": [row["case_id"] for row in regression],
        "held_out_accessed": False,
        "max_metric_calls": max_metric_calls,
        "max_candidate_proposals": max_proposals,
        "acceptance_criterion": "strict_improvement",
        "engine_candidate_count": len(getattr(result, "candidates", [])),
        "best_candidate_index": int(getattr(result, "best_idx", 0)),
        "reflections": proposer.reflections,
        "evaluations": evaluations,
        "claim_boundary": "GEPA finalist selected on development/regression next-decision simulations; held-out and matched voice gates remain required.",
    }
    write_json(OUTPUT / "lineage.json", lineage)
    lineage["mlflow"] = log_optimizer(lineage, OUTPUT)
    write_json(OUTPUT / "lineage.json", lineage)
    return lineage


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--max-metric-calls", type=int, default=48)
    parser.add_argument("--max-proposals", type=int, default=4)
    args = parser.parse_args()
    result = run_gepa(args.seed, args.max_metric_calls, args.max_proposals)
    print(json.dumps({key: result[key] for key in ("optimizer", "seed_sha256", "candidate_artifact", "engine_candidate_count", "best_candidate_index", "held_out_accessed", "claim_boundary")}, indent=2))


if __name__ == "__main__":
    main()
