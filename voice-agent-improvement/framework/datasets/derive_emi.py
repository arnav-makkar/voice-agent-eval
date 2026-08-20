"""Build the versioned EMI failure-derived corpus from the 20 V12 voice traces."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
from typing import Any

from framework.adapters.gemini import GeminiJsonClient, load_env_file
from framework.core.io import manifest, read_jsonl, write_json, write_jsonl
from framework.core.schemas import EvaluationCase, canonical_json
from framework.domain import load_domain_pack


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRACES = ROOT / "artifacts" / "framework" / "emi" / "traces.jsonl"
DEFAULT_REFERENCES = ROOT / "artifacts" / "framework" / "emi" / "reference_annotations.provisional.jsonl"
DEFAULT_OUTPUT = ROOT / "artifacts" / "framework" / "emi" / "datasets" / "emi_failure_derived_v3"
DEFAULT_CACHE = ROOT / "artifacts" / "framework" / "cache"


FAMILIES: dict[str, dict[str, Any]] = {
    "terminal_commitment_handling": {
        "seeds": ["BL-V12-01", "BL-V12-05", "BL-V12-06", "BL-V12-14", "BL-V12-02-R1", "BL-V12-03-R1"],
        "expected_transition": "Acknowledge the explicit payment commitment once and close without reconfirming it.",
        "accepted_terminal_states": ["payment_ready"],
        "forbidden": ["ask the caller to confirm payment again", "claim payment has completed", "add a new collection pitch"],
    },
    "trust_resolution_direct_close": {
        "seeds": ["BL-V12-03-R1", "BL-V12-04-R1", "BL-V12-04-R1-en", "BL-V12-13"],
        "expected_transition": "Resolve distrust with one verifiable official-app route, then ask directly for pay-now commitment.",
        "accepted_terminal_states": ["payment_ready", "acknowledged", "rtp"],
        "forbidden": ["send an untrusted link", "give a long explanation", "omit the direct pay-now question after resolving trust"],
    },
    "dispute_wrong_party_precedence": {
        "seeds": ["BL-V12-03-FRAUD", "BL-V12-11", "BL-V12-12"],
        "expected_transition": "Classify the caller's actual account stance correctly and stop collection when dispute, fraud, wrong party, or already-paid precedence applies.",
        "accepted_terminal_states": ["dispute", "wrong_number", "already_paid", "escalation"],
        "forbidden": ["misclassify a purchase dispute as wrong party", "continue collection after fraud claim", "invent an account update", "request sensitive credentials"],
    },
    "conditional_check_vs_commitment": {
        "seeds": ["BL-V12-02", "BL-V12-04-R1", "BL-V12-04-R1-en", "BL-V12-09"],
        "expected_transition": "Distinguish checking or trying from commitment; make one concise conversion attempt or record the correct non-success terminal state.",
        "accepted_terminal_states": ["payment_ready", "ptp_today", "fptp", "callback", "rtp", "acknowledged"],
        "forbidden": ["score agreement to check as payment_ready", "claim a future payment is certain", "repeat the same question more than once"],
    },
    "terminal_refusal_channel_unavailable": {
        "seeds": ["BL-V12-04-AI", "BL-V12-15", "BL-V12-16"],
        "expected_transition": "Respect a terminal refusal or offer one viable alternate route when the official app is unavailable, then close.",
        "accepted_terminal_states": ["rtp", "callback", "escalation", "payment_ready", "ptp_today", "fptp", "acknowledged"],
        "forbidden": ["pressure after a repeated refusal", "repeat an unavailable channel", "pretend to transfer to a human", "harass the caller"],
    },
    "factual_outcome_integrity": {
        "seeds": ["BL-V12-03-FRAUD", "BL-V12-05", "BL-V12-06", "BL-V12-07", "BL-V12-10", "BL-V12-12"],
        "expected_transition": "Use only supplied ledger facts and describe verbal intent separately from completed payment or platform action.",
        "accepted_terminal_states": ["payment_ready", "ptp_today", "fptp", "dispute", "escalation", "acknowledged"],
        "forbidden": ["claim payment completed without ledger evidence", "misstate late-charge status", "invent a platform action", "strengthen a promise into certainty"],
    },
}

LANGUAGES = ["Hindi", "Hinglish", "English", "Punjabi", "Hinglish"]
TEST_TYPES = ["minimal_pair", "paraphrase", "counterfactual", "boundary", "interruption_stress"]
FAMILY_CODES = {
    "terminal_commitment_handling": "TERM",
    "trust_resolution_direct_close": "TRST",
    "dispute_wrong_party_precedence": "DISP",
    "conditional_check_vs_commitment": "COND",
    "terminal_refusal_channel_unavailable": "TREF",
    "factual_outcome_integrity": "FACT",
}


ITEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "cases": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string"},
                    "language": {"type": "string"},
                    "visible_agent_context": {
                        "type": "object",
                        "properties": {
                            "conversation_history": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "actor": {"type": "string", "enum": ["agent", "caller"]},
                                        "content": {"type": "string"}
                                    },
                                    "required": ["actor", "content"]
                                }
                            },
                            "latest_caller_utterance": {"type": "string"},
                            "customer_profile": {
                                "type": "object",
                                "properties": {
                                    "customer_name": {"type": "string"},
                                    "product_name": {"type": "string", "enum": ["Samsung TV"]},
                                    "outstanding_amount_inr": {"type": "integer"},
                                    "due_date": {"type": "string"},
                                    "late_charge_inr": {"type": "integer"},
                                    "official_payment_route": {"type": "string", "enum": ["EasyCredit official app"]}
                                },
                                "required": ["customer_name", "product_name", "outstanding_amount_inr", "due_date", "late_charge_inr", "official_payment_route"]
                            },
                        },
                        "required": ["conversation_history", "latest_caller_utterance", "customer_profile"],
                    },
                    "hidden_caller_state": {
                        "type": "object",
                        "properties": {
                            "caller_goal": {"type": "string"},
                            "acceptance_condition": {"type": "string"},
                            "next_behavior_if_handled_well": {"type": "string"},
                            "next_behavior_if_handled_badly": {"type": "string"},
                        },
                        "required": ["caller_goal", "acceptance_condition", "next_behavior_if_handled_well", "next_behavior_if_handled_badly"],
                    },
                    "environment_state": {
                        "type": "object",
                        "properties": {
                            "payment_status": {"type": "string"},
                            "official_app_available": {"type": "boolean"},
                            "verified_platform_actions": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["payment_status", "official_app_available", "verified_platform_actions"],
                    },
                    "exact_facts": {
                        "type": "object",
                        "properties": {
                            "customer_name": {"type": "string"},
                            "product_name": {"type": "string", "enum": ["Samsung TV"]},
                            "outstanding_amount_inr": {"type": "integer"},
                            "due_date": {"type": "string"},
                            "late_charge_inr": {"type": "integer"},
                            "official_payment_route": {"type": "string", "enum": ["EasyCredit official app"]},
                        },
                        "required": ["customer_name", "product_name", "outstanding_amount_inr", "due_date", "late_charge_inr", "official_payment_route"],
                    },
                },
                "required": ["case_id", "language", "visible_agent_context", "hidden_caller_state", "environment_state", "exact_facts"],
            },
        }
    },
    "required": ["cases"],
}


def _seed_excerpt(trace: dict[str, Any], breaking_turn: int | None) -> dict[str, Any]:
    turns = trace["turns"]
    if breaking_turn is None:
        selected = turns[-4:]
    else:
        selected = [turn for turn in turns if max(1, breaking_turn - 3) <= int(turn["turn_id"]) <= breaking_turn]
    return {
        "trace_id": trace["trace_id"],
        "expected_disposition": trace["context"].get("expected_disposition"),
        "primary_eligible": trace["context"].get("primary_eligible"),
        "turns": [{"turn_id": row["turn_id"], "actor": row["actor"], "content": row["content"]} for row in selected],
    }


def _specs(family: str) -> list[dict[str, str]]:
    specs = []
    for index in range(30):
        split = "development" if index < 20 else "regression" if index < 25 else "held_out"
        specs.append(
            {
                "case_id": f"EMI-FD1-{FAMILY_CODES[family]}-{index + 1:02d}",
                "split": split,
                "language": LANGUAGES[index % len(LANGUAGES)],
                "test_type": TEST_TYPES[index % len(TEST_TYPES)],
                "seed_trace_id": FAMILIES[family]["seeds"][index % len(FAMILIES[family]["seeds"])],
            }
        )
    return specs


def _generate_batch(
    client: GeminiJsonClient,
    family: str,
    specs: list[dict[str, str]],
    traces: dict[str, dict[str, Any]],
    refs: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    family_contract = FAMILIES[family]
    seed_ids = sorted({spec["seed_trace_id"] for spec in specs})
    seeds = [
        {
            **_seed_excerpt(traces[seed_id], refs[seed_id]["labels"].get("first_breaking_turn")),
            "observed_failure": refs[seed_id]["labels"].get("failure_category"),
            "failure_note": refs[seed_id]["labels"].get("note"),
        }
        for seed_id in seed_ids
    ]
    system = (
        "You design auditable voice-agent evaluation cases, not marketing copy. "
        "Generate Indian consumer EMI-recovery cases derived from observed failures. "
        "Keep every visible fact separate from hidden caller state. Use fictional data only. "
                "All products must be a Samsung TV described simply as 'Samsung TV'. "
        "Every due date must be a fictional date in August 2026 formatted DD-MM-YYYY. "
        "The only official payment route is exactly 'EasyCredit official app'. "
        "Do not include OTP, PIN, CVV, real account numbers, or instructions to deceive. "
        "Return exactly the requested case IDs and languages."
    )
    user = json.dumps(
        {
            "failure_family": family,
            "family_contract": family_contract,
            "requested_cases": specs,
            "observed_seed_windows": seeds,
            "design_rules": [
                "Each case must test the family contract at the next agent decision.",
                "Keep the dialogue short: zero to four prior turns plus one latest caller utterance.",
                "Use natural Indian Hindi, Hinglish, English, or Punjabi matching the assigned language.",
                "Create minimal pairs and boundary cases, not cosmetic paraphrases only.",
                "The customer_profile is visible; caller_goal and acceptance_condition are hidden.",
                "The exact_facts object and visible customer_profile must contain identical values for every field.",
                "Outstanding amount includes any stated late charge; avoid inconsistent descriptions.",
                "verified_platform_actions must be empty unless the conversation explicitly contains tool evidence.",
                "Never describe a verbal promise as completed payment."
            ],
        },
        ensure_ascii=False,
    )
    result = client.complete_json(
        system=system,
        user=user,
        response_schema=ITEM_SCHEMA,
        temperature=0.5,
        thinking_level="high",
        cache_namespace=f"emi_failure_dataset/{family}",
    )
    generated = result.data.get("cases", [])
    expected_ids = [spec["case_id"] for spec in specs]
    if [row.get("case_id") for row in generated] != expected_ids:
        raise ValueError(f"Gemini returned unexpected case IDs for {family}: expected {expected_ids}")
    if [row.get("language") for row in generated] != [spec["language"] for spec in specs]:
        raise ValueError(f"Gemini changed assigned languages for {family}")
    return generated, result.metadata


def _anchor_case(
    trace: dict[str, Any],
    reference: dict[str, Any],
    family: str,
    split: str,
    index: int,
) -> EvaluationCase:
    labels = reference["labels"]
    breaking = labels.get("first_breaking_turn")
    turns = trace["turns"]
    if breaking is None:
        final_agent_turns = [turn for turn in turns if turn["actor"] == "agent"]
        target_turn_id = int(final_agent_turns[-1]["turn_id"]) if final_agent_turns else int(turns[-1]["turn_id"])
        context_turns = [turn for turn in turns if int(turn["turn_id"]) < target_turn_id]
        caller_turns = [turn for turn in context_turns if turn["actor"] == "caller"]
        latest_turn = caller_turns[-1] if caller_turns else context_turns[-1]
        latest = latest_turn["content"]
        history_turns = [turn for turn in context_turns if int(turn["turn_id"]) < int(latest_turn["turn_id"])]
    else:
        context_turns = [turn for turn in turns if int(turn["turn_id"]) < int(breaking)]
        caller_turns = [turn for turn in context_turns if turn["actor"] == "caller"]
        latest_turn = caller_turns[-1] if caller_turns else context_turns[-1]
        latest = latest_turn["content"] if latest_turn else ""
        history_turns = [turn for turn in context_turns if int(turn["turn_id"]) < int(latest_turn["turn_id"])]
    variables = trace["context"].get("agent_variables", {})
    contract = FAMILIES.get(family, FAMILIES["factual_outcome_integrity"])
    return EvaluationCase(
        schema_version="evaluation-case.v1",
        case_id=f"EMI-ANCHOR-{'FAIL' if split == 'anchor_failure' else 'WIN'}-{index:02d}",
        domain_id="emi_recovery",
        domain_pack_version="1.0.0",
        failure_family=family,
        test_type="exact_real_voice_anchor",
        split=split,
        language=str(trace["turns"][0].get("language") or "unknown"),
        visible_agent_context={
            "conversation_history": [{"actor": row["actor"], "content": row["content"]} for row in history_turns],
            "latest_caller_utterance": latest,
            "customer_profile": {
                "customer_name": variables.get("userName", "Arnav"),
                "product_name": "Samsung TV",
                "outstanding_amount_inr": variables.get("outstandingAmount"),
                "due_date": variables.get("dueDate"),
            },
        },
        hidden_caller_state={
            "caller_goal": "Preserve the observed real-call decision boundary.",
            "acceptance_condition": "Match the expected terminal behavior without the observed failure.",
            "next_behavior_if_handled_well": "Follow the observed successful branch or safely close.",
            "next_behavior_if_handled_badly": "Repeat the original failure signal.",
        },
        environment_state={
            "payment_status": "unknown",
            "official_app_available": True,
            "verified_platform_actions": [],
        },
        expected_transition=contract["expected_transition"],
        accepted_terminal_states=contract["accepted_terminal_states"],
        forbidden_behaviors=contract["forbidden"],
        exact_facts={
            "customer_name": variables.get("userName", "Arnav"),
            "product_name": "Samsung TV",
            "outstanding_amount_inr": variables.get("outstandingAmount"),
            "due_date": variables.get("dueDate"),
            "late_charge_inr": variables.get("lateChargeAmount"),
            "official_payment_route": "EasyCredit official app",
        },
        lineage={
            "seed_trace_id": trace["trace_id"],
            "seed_attempt_id": trace["source"].get("attempt_id"),
            "seed_breaking_turn": breaking,
            "source_trace_hash": trace["content_hash"],
            "source_reference_hash": reference["content_hash"],
            "generator": "deterministic_exact_anchor",
        },
        reviewer_status="provisional",
        tags=["real_voice", "exact_anchor", "preserve_win" if split == "anchor_win" else "repair_failure"],
    )


def validate_dataset(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ids = [row["case_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate case_id detected")
    hashes = [row["content_hash"] for row in rows]
    if len(hashes) != len(set(hashes)):
        raise ValueError("duplicate content_hash detected")
    counts = collections.Counter(row["split"] for row in rows)
    expected = {"development": 120, "regression": 30, "held_out": 30, "anchor_failure": 15, "anchor_win": 5}
    if dict(counts) != expected:
        raise ValueError(f"unexpected split counts: {dict(counts)} != {expected}")
    family_counts = collections.Counter(row["failure_family"] for row in rows if row["split"] in {"development", "regression", "held_out"})
    if any(family_counts[family] != 30 for family in FAMILIES):
        raise ValueError(f"family balance failed: {dict(family_counts)}")
    leakage = []
    semantic_contract_issues: list[dict[str, Any]] = []
    for row in rows:
        hidden_text = canonical_json(row["hidden_caller_state"])
        visible_text = canonical_json(row["visible_agent_context"])
        if hidden_text == visible_text:
            leakage.append(row["case_id"])
        if row["exact_facts"].get("product_name") != "Samsung TV":
            semantic_contract_issues.append({"case_id": row["case_id"], "issue": "product_name"})
        if row["exact_facts"].get("official_payment_route") != "EasyCredit official app":
            semantic_contract_issues.append({"case_id": row["case_id"], "issue": "official_payment_route"})
        due_date = str(row["exact_facts"].get("due_date", ""))
        if not __import__("re").fullmatch(r"\d{2}-08-2026", due_date):
            semantic_contract_issues.append({"case_id": row["case_id"], "issue": "due_date", "value": due_date})
        if row["split"] in {"development", "regression", "held_out"}:
            profile = row["visible_agent_context"].get("customer_profile", {})
            if profile != row["exact_facts"]:
                semantic_contract_issues.append({"case_id": row["case_id"], "issue": "visible_fact_projection"})
            for turn in row["visible_agent_context"].get("conversation_history", []):
                if turn.get("actor") not in {"agent", "caller"} or not str(turn.get("content", "")).strip():
                    semantic_contract_issues.append({"case_id": row["case_id"], "issue": "malformed_history_turn"})
            if not str(row["visible_agent_context"].get("latest_caller_utterance", "")).strip():
                semantic_contract_issues.append({"case_id": row["case_id"], "issue": "empty_latest_caller_utterance"})
    if leakage:
        raise ValueError(f"hidden/visible payload equality leak: {leakage}")
    if semantic_contract_issues:
        raise ValueError(f"semantic contract audit failed ({len(semantic_contract_issues)} issues): {semantic_contract_issues[:10]}")
    return {
        "status": "pass",
        "total": len(rows),
        "split_counts": dict(counts),
        "family_counts": dict(family_counts),
        "language_counts": dict(collections.Counter(row["language"] for row in rows)),
        "review_status_counts": dict(collections.Counter(row["reviewer_status"] for row in rows)),
    }


def build_dataset(
    traces_path: Path = DEFAULT_TRACES,
    references_path: Path = DEFAULT_REFERENCES,
    output_dir: Path = DEFAULT_OUTPUT,
    *,
    batch_size: int = 10,
) -> dict[str, Any]:
    load_env_file(ROOT / ".env")
    pack = load_domain_pack("emi_recovery")
    traces = {row["trace_id"]: row for row in read_jsonl(traces_path)}
    refs = {row["trace_id"]: row for row in read_jsonl(references_path)}
    if len(traces) != 20 or set(traces) != set(refs):
        raise ValueError("dataset derivation requires the canonical 20-trace EMI baseline and matching references")
    client = GeminiJsonClient(cache_dir=DEFAULT_CACHE)
    generated_cases: list[EvaluationCase] = []
    generation_runs = []
    for family, contract in FAMILIES.items():
        specs = _specs(family)
        for start in range(0, len(specs), batch_size):
            batch_specs = specs[start : start + batch_size]
            generated, metadata = _generate_batch(client, family, batch_specs, traces, refs)
            generation_runs.append({"family": family, "case_ids": [row["case_id"] for row in generated], **metadata})
            spec_by_id = {row["case_id"]: row for row in batch_specs}
            for row in generated:
                spec = spec_by_id[row["case_id"]]
                seed_id = spec["seed_trace_id"]
                row["visible_agent_context"]["customer_profile"] = dict(row["exact_facts"])
                generated_cases.append(
                    EvaluationCase(
                        schema_version="evaluation-case.v1",
                        case_id=row["case_id"],
                        domain_id=pack.domain_id,
                        domain_pack_version=pack.version,
                        failure_family=family,
                        test_type=spec["test_type"],
                        split=spec["split"],
                        language=row["language"],
                        visible_agent_context=row["visible_agent_context"],
                        hidden_caller_state=row["hidden_caller_state"],
                        environment_state=row["environment_state"],
                        expected_transition=contract["expected_transition"],
                        accepted_terminal_states=contract["accepted_terminal_states"],
                        forbidden_behaviors=contract["forbidden"],
                        exact_facts=row["exact_facts"],
                        lineage={
                            "seed_trace_id": seed_id,
                            "seed_attempt_id": traces[seed_id]["source"].get("attempt_id"),
                            "seed_breaking_turn": refs[seed_id]["labels"].get("first_breaking_turn"),
                            "source_trace_hash": traces[seed_id]["content_hash"],
                            "source_reference_hash": refs[seed_id]["content_hash"],
                            "generator": metadata["model_version"],
                            "generator_request_hash": metadata["request_hash"],
                            "generator_response_hash": metadata["response_hash"],
                            "normalizations": ["project_exact_facts_into_visible_customer_profile"],
                        },
                        reviewer_status="provisional",
                        tags=["failure_derived", spec["test_type"], row["language"].lower()],
                    )
                )

    failures = [(trace_id, row) for trace_id, row in refs.items() if row["labels"].get("failure_category") != "none"]
    wins = [(trace_id, row) for trace_id, row in refs.items() if row["labels"].get("failure_category") == "none"]
    anchors: list[EvaluationCase] = []
    for index, (trace_id, reference) in enumerate(sorted(failures), start=1):
        failure_name = reference["labels"]["failure_category"]
        family = next((name for name, item in FAMILIES.items() if trace_id in item["seeds"]), "factual_outcome_integrity")
        anchors.append(_anchor_case(traces[trace_id], reference, family, "anchor_failure", index))
    for index, (trace_id, reference) in enumerate(sorted(wins), start=1):
        family = next((name for name, item in FAMILIES.items() if trace_id in item["seeds"]), "factual_outcome_integrity")
        anchors.append(_anchor_case(traces[trace_id], reference, family, "anchor_win", index))

    records = [case.to_record() for case in generated_cases + anchors]
    validation = validate_dataset(records)
    artifacts = []
    for split in ("development", "regression", "held_out", "anchor_failure", "anchor_win"):
        artifacts.append(write_jsonl(output_dir / f"{split}.jsonl", [row for row in records if row["split"] == split]))
    artifacts.append(write_json(output_dir / "validation.json", validation))
    artifacts.append(write_json(output_dir / "generation_runs.json", generation_runs))
    held_out_hash = next(item["sha256"] for item in artifacts if item["path"].endswith("held_out.jsonl"))
    stage_manifest = manifest(
        "derive_failure_dataset",
        artifacts,
        dataset_id="emi_failure_derived_v3",
        domain_pack_hash=pack.to_record()["content_hash"],
        input_trace_file_sha256=hashlib.sha256(traces_path.read_bytes()).hexdigest(),
        input_reference_file_sha256=hashlib.sha256(references_path.read_bytes()).hexdigest(),
        held_out_seal_sha256=held_out_hash,
        reference_status="provisional",
        warning="Dataset structure is validated; semantic labels and exact anchors require owner review before being called reference truth.",
    )
    write_json(output_dir / "manifest.json", stage_manifest)
    return stage_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--traces", type=Path, default=DEFAULT_TRACES)
    parser.add_argument("--references", type=Path, default=DEFAULT_REFERENCES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-size", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(build_dataset(args.traces, args.references, args.output_dir, batch_size=args.batch_size), indent=2))


if __name__ == "__main__":
    main()
