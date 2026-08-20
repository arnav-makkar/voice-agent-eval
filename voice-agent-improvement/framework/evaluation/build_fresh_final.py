"""Generate and seal a fresh, group-separated final test after method freeze."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from framework.adapters.gemini import GeminiJsonClient, load_env_file
from framework.core.io import write_json, write_jsonl
from framework.evaluation.build_emi_scenarios import COMMON_FORBIDDEN, _context, _initial
from framework.evaluation.contracts import EvaluationScenario, UserStep


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "artifacts" / "framework" / "emi" / "dynamic_scenarios_v1"

DISPOSITIONS = ["payment_ready", "ptp_today", "fptp", "callback", "dispute", "already_paid", "wrong_number", "rtp", "acknowledged", "escalation"]
TOOL_NAMES = ["none", "record_promise_to_pay", "schedule_callback"]

# Deeply nested 12-card schemas exceed Gemini's structured-output complexity
# limit.  Keep the API-level envelope tiny, then enforce the full contract in
# `_validate_blueprints` before any final artifact is sealed.
SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "blueprints_json": {
            "type": "string",
            "description": "A JSON array containing exactly 12 blueprint objects described by the request.",
        }
    },
    "required": ["blueprints_json"],
}


def _validate_blueprints(blueprints: list[dict[str, Any]]) -> dict[str, Any]:
    if len(blueprints) != 12:
        raise ValueError("fresh final generator must return exactly 12 cards")
    scripts = []
    languages = set()
    dispositions = set()
    tools = set()
    internal_terms = {"evaluation", "candidate", "hidden state", "tool call", "scenario id"}
    for index, item in enumerate(blueprints, start=1):
        required = {
            "failure_family", "language", "user_goal", "persona", "user_steps",
            "accepted_disposition", "required_tool", "tool_arguments", "perturbations",
        }
        missing = required - set(item)
        if missing:
            raise ValueError(f"fresh final card {index} is missing {sorted(missing)}")
        item["language"] = str(item["language"]).strip().lower()
        item["accepted_disposition"] = str(item["accepted_disposition"]).strip().lower().replace(" ", "_")
        item["required_tool"] = str(item["required_tool"]).strip().lower().replace(" ", "_")
        if item["language"] not in {"hindi", "hinglish", "english", "punjabi"}:
            raise ValueError(f"fresh final card {index} has an unsupported language")
        if item["accepted_disposition"] not in DISPOSITIONS or item["required_tool"] not in TOOL_NAMES:
            raise ValueError(
                f"fresh final card {index} has an unsupported outcome contract: "
                f"{item['accepted_disposition']!r}, {item['required_tool']!r}"
            )
        if not isinstance(item["user_steps"], list) or not 1 <= len(item["user_steps"]) <= 5:
            raise ValueError(f"fresh final card {index} must contain 1-5 user steps")
        if any(not {"text", "intent"}.issubset(set(step)) for step in item["user_steps"]):
            raise ValueError(f"fresh final card {index} has a malformed user step")
        script = " ".join(step["text"].strip().lower() for step in item["user_steps"])
        if not script or any(term in script for term in internal_terms):
            raise ValueError(f"fresh final card {index} leaks evaluation mechanics or has no caller script")
        scripts.append(script)
        languages.add(item["language"])
        disposition = item["accepted_disposition"]
        dispositions.add(disposition)
        tool = item["required_tool"]
        tools.add(tool)
        arguments = item["tool_arguments"]
        if tool == "record_promise_to_pay":
            if disposition not in {"ptp_today", "fptp"} or not re.fullmatch(r"\d{2}-\d{2}-\d{4}", str(arguments.get("date", ""))):
                raise ValueError(f"fresh final card {index} has an invalid promise tool contract")
        elif tool == "schedule_callback":
            if disposition != "callback" or not re.fullmatch(r"\d{2}-\d{2}-\d{4}", str(arguments.get("date", ""))) or not arguments.get("time_window"):
                raise ValueError(f"fresh final card {index} has an invalid callback tool contract")
        elif disposition in {"ptp_today", "fptp", "callback"}:
            raise ValueError(f"fresh final card {index} omits the state-changing tool for {disposition}")
    if len(set(scripts)) != len(scripts):
        raise ValueError("fresh final contains duplicate caller scripts")
    required_languages = {"english", "punjabi"}
    required_dispositions = {"payment_ready", "callback", "acknowledged"}
    if not required_languages.issubset(languages):
        raise ValueError("fresh final lacks required English/Punjabi coverage")
    if not required_dispositions.issubset(dispositions) or not ({"fptp", "ptp_today"} & dispositions):
        raise ValueError("fresh final lacks required outcome coverage")
    if not {"record_promise_to_pay", "schedule_callback"}.issubset(tools):
        raise ValueError("fresh final lacks required executable tool coverage")
    return {
        "unique_scripts": True,
        "languages": sorted(languages),
        "dispositions": sorted(dispositions),
        "tools": sorted(tools),
        "internal_mechanics_leakage": False,
    }


def build(baseline_hash: str, candidate_hash: str, evaluator_hash: str, output: Path = OUTPUT) -> dict[str, Any]:
    final_path = output / "fresh_final.jsonl"
    if final_path.exists():
        raise FileExistsError("fresh final already exists; do not regenerate after access")
    load_env_file(ROOT / ".env")
    # Use the same explicitly versioned Pro model as the semantic judge.  The
    # generic `gemini-pro-latest` alias rejected the structured-output request
    # in an actual dry run, while this version is already verified in this lab.
    client = GeminiJsonClient(model="gemini-3.1-pro-preview", cache_dir=None)
    nonce = uuid.uuid4().hex
    response = client.complete_json(
        system=(
            "Author exactly 12 difficult but realistic EMI recovery evaluation cards for an uninterested caller. "
            "Cards must be complete multi-turn decision paths, mutually distinct, and not mere paraphrases. "
            "Test outcome precedence, conditional versus firm commitment, app unavailable, distrust, credentials, language switching, interruption, callback/date capture, and exceptions. "
            "Do not mention evaluation, candidate prompts, hidden labels, or tools in caller speech. Do not invent a business action. "
            "For a firm future/today promise require record_promise_to_pay with DD-MM-YYYY; for confirmed callback require schedule_callback with date and narrow IST time_window; otherwise required_tool=none. "
            "Return blueprints_json as a serialized JSON array. Every object must have failure_family, language, user_goal, persona (object), user_steps (1-5 objects with text and intent), accepted_disposition, required_tool, tool_arguments (object), and perturbations (array of strings)."
            f" accepted_disposition must be exactly one of {DISPOSITIONS}. required_tool must be exactly one of {TOOL_NAMES}. language must be exactly hindi, hinglish, english, or punjabi."
        ),
        user=json.dumps(
            {
                "generation_nonce": nonce,
                "today": "17-08-2026",
                "tomorrow": "18-08-2026",
                "cutoff": "22-08-2026",
                "official_channel": "EasyCredit app",
                "required_coverage": [
                    "at least three conditional-language traps",
                    "at least two terminal exception/precedence cases",
                    "English and Punjabi",
                    "one exact future promise",
                    "one callback",
                    "one explicit pay-now",
                    "one app-unavailable case that forbids an invented website",
                ],
                "required_slot_contracts": [
                    {"slot": 1, "language": "english", "accepted_disposition": "payment_ready", "required_tool": "none"},
                    {"slot": 2, "language": "punjabi", "accepted_disposition": "callback", "required_tool": "schedule_callback"},
                    {"slot": 3, "language": "hinglish", "accepted_disposition": "fptp", "required_tool": "record_promise_to_pay"},
                    {"slot": 4, "language": "hindi", "accepted_disposition": "acknowledged", "required_tool": "none"},
                ],
            },
            ensure_ascii=False,
        ),
        response_schema=SCHEMA,
        temperature=0.25,
        thinking_level="high",
        cache_namespace="fresh_final_once",
        use_cache=False,
    )
    try:
        blueprints = json.loads(response.data["blueprints_json"])
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("fresh final generator returned an invalid blueprint payload") from exc
    if not isinstance(blueprints, list) or not all(isinstance(item, dict) for item in blueprints):
        raise ValueError("fresh final blueprint payload must be a JSON array of objects")
    contract_validation = _validate_blueprints(blueprints)
    scenarios = []
    for offset, blueprint in enumerate(blueprints, start=1):
        context = _context(100 + offset)
        disposition = blueprint["accepted_disposition"]
        required_actions = []
        if blueprint["required_tool"] != "none":
            required_actions.append({"name": blueprint["required_tool"], "arguments": blueprint["tool_arguments"]})
        scenarios.append(
            EvaluationScenario(
                schema_version="evaluation-scenario.v1",
                scenario_id=f"EMI-FINAL-{offset:03d}",
                domain_id="emi_recovery",
                split="fresh_final",
                source_group=f"fresh-gemini-{nonce[:8]}-{offset:03d}",
                failure_family=blueprint["failure_family"],
                language=blueprint["language"],
                user_goal=blueprint["user_goal"],
                persona=blueprint["persona"],
                visible_context=context,
                hidden_state={"target_disposition": disposition, "generation_nonce_hash": hashlib.sha256(nonce.encode()).hexdigest()},
                initial_environment=_initial(context),
                user_steps=[UserStep(**item) for item in blueprint["user_steps"]],
                accepted_dispositions=[disposition],
                expected_state={"disposition": disposition},
                required_actions=required_actions,
                forbidden_phrases=COMMON_FORBIDDEN,
                perturbations=blueprint["perturbations"],
                reviewer_status="provisional_generated_final",
            )
        )
    rows = [scenario.to_record() for scenario in scenarios]
    artifact = write_jsonl(final_path, rows)
    created_at = datetime.now(UTC).isoformat()
    seal = {
        "schema_version": "fresh-final-seal.v1",
        "created_at": created_at,
        "dataset_sha256": artifact["sha256"],
        "records": 12,
        "baseline_frozen_sha256": baseline_hash,
        "candidate_method_frozen_sha256": candidate_hash,
        "evaluator_frozen_sha256": evaluator_hash,
        "generator_model": response.metadata["model_version"],
        "generator_request_hash": response.metadata["request_hash"],
        "source_independence": "new model-authored source groups; no real-call or static-case lineage",
        "review_status": "automated_contract_validation_complete_owner_semantic_review_pending",
        "contract_validation": contract_validation,
        "access_policy": "run baseline and frozen candidate once; no subsequent candidate tuning may use these cases",
    }
    write_json(output / "fresh_final_seal.json", seal)
    write_json(output / "fresh_final_access_log.json", {"created_at": created_at, "accessed_by_improvement": False, "evaluation_runs": []})
    return seal


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-hash", required=True)
    parser.add_argument("--candidate-hash", required=True)
    parser.add_argument("--evaluator-hash", required=True)
    parser.add_argument("--freeze", type=Path, help="Optional method-freeze artifact; supplied hashes must match it")
    args = parser.parse_args()
    if args.freeze:
        frozen = json.loads(args.freeze.read_text(encoding="utf-8"))
        expected = (
            frozen["baseline_prompt_sha256"],
            frozen["finalist_prompt_sha256"],
            frozen["evaluator_bundle_sha256"],
        )
        supplied = (args.baseline_hash, args.candidate_hash, args.evaluator_hash)
        if supplied != expected:
            raise ValueError("fresh-final hashes do not match the method-freeze artifact")
    print(json.dumps(build(args.baseline_hash, args.candidate_hash, args.evaluator_hash), indent=2))


if __name__ == "__main__":
    main()
