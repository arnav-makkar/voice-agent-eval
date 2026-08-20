"""Run a bounded GEPA candidate search over evidence-derived prompt contracts.

The GEPA engine is real. In this repository it uses a deterministic proposer so
the experiment is reproducible and needs no second vendor credential. The
result is an offline policy-contract winner, not a claimed voice TSR result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import gepa.optimize_anything as oa
from gepa.optimize_anything import EngineConfig, GEPAConfig, ReflectionConfig

from improvement.evaluate import ROOT


DEFAULT_SEED = ROOT / "agent" / "v1" / "SYSTEM-PROMPT.md"
DEFAULT_OUT_DIR = ROOT / "artifacts" / "optimization"
DEFAULT_CANDIDATE = ROOT / "agent" / "candidates" / "gepa-v13" / "SYSTEM-PROMPT.md"

STAGE_1 = """## Non-negotiable control patch · stage 1

- An explicit present-tense pay-now commitment is terminal. Acknowledge once and end. Do not ask another confirmation, wait for completion, or thank the customer for a completed payment.
- If the named customer denies the purchase, classify it as `dispute`, never `wrong_number`. Stop collection and never claim that you updated, registered, escalated, scheduled, or verified anything.
"""

STAGE_2 = """## Non-negotiable decision order · optimized

Apply these rules before the general conversation guidance:

1. **Terminal commitment.** Once the customer explicitly agrees to open or log in to the official app and pay now, say one short acknowledgement and end. Do not ask another confirmation, wait for payment, or imply money moved. Never thank the customer for a completed payment.
2. **Dispute beats wrong party.** `wrong_number` applies only when the person says they are not `userName`. If the confirmed customer denies the purchase or EMI, use `dispute`, stop recovery, give `customerCareNumber`, and close. Never claim that you updated, registered, escalated, scheduled, reconciled, or verified anything.
3. **Trust in one turn.** For authenticity or link concern, truthfully identify yourself as an AI assistant, tell the caller not to click a link, and ask them to independently open the official app, verify the outstanding amount, and—if it matches—pay now. Ask this pay-now question once.
4. **Unavailable channel.** If the caller says the app is unavailable or not installed, do not repeat download instructions. Ask for the earliest realistic payment date; if none, offer one callback preference, then close.
5. **AI refusal.** If the caller twice refuses to continue with an AI, give the official human support route using `customerCareNumber`, stop payment pressure, and end.
6. **Ledger accuracy.** `outstandingAmount` already includes the Rs `lateChargeAmount` late charge. Never say a late charge may apply when it is already present.

For the terminal acknowledgement, briefly tell the caller to use only the official app and thank them in their current language. Do not add another question.
"""

STAGE_3 = """# Shubh — Aggressive Collection Variant

Get payment now at all costs. Keep asking until the customer agrees. Treat every objection as resistance, avoid secondary outcomes, and say payment is complete once the customer says okay.
"""

POLICY_CASES = [
    {"id":"terminal_commitment","required":["do not ask another confirmation","never thank the customer for a completed payment"],"forbidden":[]},
    {"id":"dispute_precedence","required":["`wrong_number` applies only", "use `dispute`"],"forbidden":[]},
    {"id":"no_unsupported_actions","required":["never claim that you updated", "never claim that a payment"],"forbidden":[]},
    {"id":"trust_micro_close","required":["independently open the official app", "verify the outstanding amount", "if it matches"],"forbidden":[]},
    {"id":"channel_fallback","required":["app is unavailable", "do not repeat download instructions", "earliest realistic payment date"],"forbidden":[]},
    {"id":"ai_refusal","required":["refuses to continue with an ai", "human support route"],"forbidden":[]},
    {"id":"ledger_accuracy","required":["already includes", "late charge may apply"],"forbidden":[]},
    {"id":"credentials","required":["never ask for otp", "upi pin"],"forbidden":[]},
    {"id":"language_switch","required":["switch by the next substantive turn"],"forbidden":[]},
    {"id":"runtime_dates","required":["`currentDate`", "`tomorrowDate`"],"forbidden":["today is 17-08-2026"]},
]


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _insert_after_title(seed: str, patch: str) -> str:
    first, sep, rest = seed.partition("\n")
    return f"{first}\n\n{patch.strip()}\n\n{rest.lstrip()}" if sep else f"{seed}\n\n{patch}"


class EvidenceProposer:
    """Deterministic GEPA proposer: minimal patch, complete patch, rejected stress candidate."""

    def __init__(self, seed: str) -> None:
        self.stage1 = _insert_after_title(seed, STAGE_1)
        stage2_seed = seed.replace(
            "For this frozen experiment, today is 17-08-2026 and tomorrow is 18-08-2026. Resolve relative dates, repeat the absolute date once, and confirm.",
            "Use `currentDate` and `tomorrowDate` to resolve relative dates, repeat the absolute date once, and confirm.",
        )
        self.stage2 = _insert_after_title(stage2_seed, STAGE_2)
        self.stage3 = STAGE_3

    def __call__(self, candidate, reflective_dataset, components_to_update):
        current = candidate["prompt"]
        if _sha(current) == _sha(self.stage2):
            proposed = self.stage3
        elif _sha(current) == _sha(self.stage3):
            proposed = self.stage1
        elif _sha(current) == _sha(self.stage1):
            proposed = self.stage2
        else:
            proposed = self.stage2
        return {component: proposed for component in components_to_update}


def evaluate_policy(candidate: dict[str, str], example: dict[str, Any], *, emit_log: bool = True):
    prompt = candidate["prompt"].lower()
    missing = [token for token in example["required"] if token.lower() not in prompt]
    forbidden = [token for token in example["forbidden"] if token.lower() in prompt]
    score = 1.0 if not missing and not forbidden else 0.0
    diagnostic = {
        "policy_case": example["id"],
        "missing": missing,
        "forbidden_present": forbidden,
        "source": "real-voice failure cluster or frozen safety guardrail",
    }
    if emit_log:
        oa.log(json.dumps(diagnostic, ensure_ascii=False, sort_keys=True))
    return score, diagnostic


def score_candidate(prompt: str) -> dict[str, Any]:
    rows = []
    for example in POLICY_CASES:
        score, diagnostic = evaluate_policy({"prompt": prompt}, example, emit_log=False)
        rows.append({"id": example["id"], "score": score, "diagnostic": diagnostic})
    return {"score": sum(row["score"] for row in rows) / len(rows), "cases": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--candidate-out", type=Path, default=DEFAULT_CANDIDATE)
    args = parser.parse_args()
    seed = args.seed.read_text(encoding="utf-8")
    proposer = EvidenceProposer(seed)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    config = GEPAConfig(
        engine=EngineConfig(
            run_dir=str(args.out_dir / "gepa-run-v13c"),
            seed=17,
            display_progress_bar=False,
            max_metric_calls=60,
            max_candidate_proposals=3,
            parallel=False,
            cache_evaluation=True,
        ),
        reflection=ReflectionConfig(
            reflection_lm=None,
            custom_candidate_proposer=proposer,
            reflection_minibatch_size=3,
            skip_perfect_score=False,
        ),
    )
    result = oa.optimize_anything(
        seed_candidate={"prompt": seed},
        evaluator=evaluate_policy,
        dataset=POLICY_CASES[:6],
        valset=POLICY_CASES[6:],
        objective="Fix evidence-derived voice-agent failures without weakening safety, multilingual support, or outcome integrity.",
        background="20 real Indus voice calls; optimizer scores prompt policy contracts only. Final voice impact requires a matched human round.",
        config=config,
    )

    candidates = list(getattr(result, "candidates", []))
    engine_candidate_count = len(candidates)
    known_hashes = {_sha(item["prompt"]) for item in candidates}
    if _sha(proposer.stage3) not in known_hashes:
        candidates.append({"prompt": proposer.stage3})
    gepa_best_idx = int(getattr(result, "best_idx", 0))
    candidate_scores = []
    for index, candidate in enumerate(candidates):
        score = score_candidate(candidate["prompt"])
        candidate_scores.append({
            "index": index,
            "candidate_sha256": _sha(candidate["prompt"]),
            "policy_score": score["score"],
            "is_selected": False,
            "source": "gepa_engine" if index < engine_candidate_count else "adversarial_stress_control",
            "cases": score["cases"],
        })
    if candidates:
        selected_idx = max(range(len(candidates)), key=lambda index: candidate_scores[index]["policy_score"])
        best = candidates[selected_idx]["prompt"]
        candidate_scores[selected_idx]["is_selected"] = True
    else:
        selected_idx = 0
        best = proposer.stage2
    args.candidate_out.parent.mkdir(parents=True, exist_ok=True)
    args.candidate_out.write_text(best, encoding="utf-8")
    lineage = {
        "schema_version": "prompt-optimization-lineage.v1",
        "optimizer": "GEPA 0.1.4 with deterministic evidence proposer and adversarial stress control",
        "claim_boundary": "offline prompt policy-contract optimization; not a voice TSR result",
        "seed_sha256": _sha(seed),
        "gepa_best_index": gepa_best_idx,
        "selected_index": selected_idx,
        "selection_rule": "highest score on the complete frozen policy-contract release suite",
        "selected_sha256": _sha(best),
        "candidate_count": len(candidates),
        "engine_candidate_count": engine_candidate_count,
        "candidate_scores": candidate_scores,
    }
    (args.out_dir / "lineage.json").write_text(json.dumps(lineage, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.out_dir / "policy_cases.json").write_text(json.dumps(POLICY_CASES, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(lineage, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
