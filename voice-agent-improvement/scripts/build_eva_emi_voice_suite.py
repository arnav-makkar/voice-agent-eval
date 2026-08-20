"""Build the frozen 12-core + 6-acoustic EVA EMI voice scenario suite.

The source contracts are the project-owned dynamic EMI scenarios.  This
transformation adds EVA's hidden realtime-caller policy and an isolated state
fixture without exposing the expected outcome to the deployed Samvaad agent.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "artifacts" / "framework" / "emi" / "dynamic_scenarios_v1"
EVA_DATA = ROOT / "research" / "upstream" / "eva" / "data" / "emi_dataset.json"
EVA_SCENARIOS = ROOT / "research" / "upstream" / "eva" / "data" / "emi_scenarios"
MANIFEST = ROOT / "artifacts" / "framework" / "emi" / "eva_voice_suite_v1" / "manifest.json"

CORE_SOURCE_IDS = [
    "EMI-DYN-001",
    "EMI-DYN-003",
    "EMI-DYN-005",
    "EMI-DYN-006",
    "EMI-DYN-007",
    "EMI-DYN-008",
    "EMI-DYN-009",
    "EMI-DYN-012",
    "EMI-DYN-013",
    "EMI-DYN-014",
    "EMI-DYN-025",
    "EMI-DYN-028",
]

ACOUSTIC_CASES = [
    ("EMI-DYN-001", {"kind": "background_noise", "snr_db": 12, "seed": 1301}),
    ("EMI-DYN-001", {"kind": "low_gain", "gain": 0.4, "seed": 1302}),
    ("EMI-DYN-001", {"kind": "packet_loss", "probability": 0.08, "seed": 1303}),
    ("EMI-DYN-028", {"kind": "jitter", "max_delay_ms": 80, "seed": 1304}),
    ("EMI-DYN-012", {"kind": "background_noise", "snr_db": 15, "seed": 1305}),
    ("EMI-DYN-013", {"kind": "low_gain", "gain": 0.55, "seed": 1306}),
]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_sources() -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for name in ("development.jsonl", "validation.jsonl", "regression.jsonl"):
        for line in (SOURCE_ROOT / name).read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            rows[row["scenario_id"]] = row
    return rows


def _base_agent_variables() -> dict[str, Any]:
    fixture = json.loads((EVA_SCENARIOS / "EMI-LIVE-001.json").read_text(encoding="utf-8"))
    variables = copy.deepcopy(fixture["agent_variables"])
    variables.update(
        {
            "campaignId": "EVA_RUNTIME_RUN_ID",
            "currentDate": "19-08-2026",
            "tomorrowDate": "20-08-2026",
            "userName": "Arnav",
        }
    )
    return variables


def _normalize_for_current_date(source: dict[str, Any]) -> dict[str, Any]:
    row = copy.deepcopy(source)
    if row["scenario_id"] == "EMI-DYN-005":
        row["user_steps"][1]["text"] = "abhi busy hoon, kal shaam paanch se chhe ke beech call karna"
        row["user_steps"][2]["text"] = "haan, 20 August 5 se 6 baje"
        row["required_actions"][0]["arguments"]["date"] = "20-08-2026"
    return row


def _record(source: dict[str, Any], record_id: str, acoustic: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
    source = _normalize_for_current_date(source)
    variables = _base_agent_variables()
    variables["outstandingAmount"] = source["visible_context"]["outstandingAmount"]
    variables["emiAmount"] = source["visible_context"]["outstandingAmount"]
    variables["transactionReference"] = source["initial_environment"]["account_id"]
    steps = [step["text"] for step in source["user_steps"]]
    required_tools = source.get("required_actions", [])
    expected_outcome = source["accepted_dispositions"][0]

    customer = {
        "name": "Arnav",
        "product": "Samsung Smart TV",
        "merchant": "Croma",
        "emi_amount": source["visible_context"]["outstandingAmount"],
        "payment_status": source["initial_environment"]["payment_status"],
        "outcome": None,
        "promise_to_pay_date": None,
        "callback_at": None,
    }
    expected_customer = copy.deepcopy(customer)
    expected_customer["outcome"] = expected_outcome
    for action in required_tools:
        if action["name"] == "record_promise_to_pay":
            expected_customer["promise_to_pay_date"] = action["arguments"]["date"]
        elif action["name"] == "schedule_callback":
            expected_customer["callback_at"] = {
                "date": action["arguments"]["date"],
                "time_window": action["arguments"]["time_window"],
            }

    behavior = [
        f"Start with this short natural response in {source['language']}: {steps[0]}",
        "Do not volunteer the amount, product, expected outcome, or the rest of your script before Shubh gives you a reason to respond.",
    ]
    behavior.extend(
        f"When the conversation reaches the next relevant point, respond naturally but preserve this meaning exactly: {text}"
        for text in steps[1:]
    )
    behavior.extend(
        [
            "If Shubh repeats a resolved question, point out the repetition once instead of changing your answer.",
            "Never provide an OTP, UPI PIN, CVV, card number, password, or claim that money actually moved.",
        ]
    )
    if acoustic:
        behavior.append("Keep following the hidden goal even if the audio condition causes a repeat; ask for one repeat rather than inventing content.")

    tool_criterion = ""
    if required_tools:
        names = ", ".join(action["name"] for action in required_tools)
        tool_criterion = f" The required backend action is executed exactly once: {names}."
    must_have = [
        f"Shubh reaches the correct terminal outcome {expected_outcome} without forbidden pressure or fabricated completion.{tool_criterion}"
    ]
    nice_to_have = ["Shubh uses short turns, does not repeat resolved questions, and closes immediately after the terminal outcome."]
    resolution = (
        f"After Shubh accurately acknowledges the final {expected_outcome} outcome"
        + (" and the required tool effect is complete" if required_tools else "")
        + ", say a brief goodbye and call end_call."
    )
    failure = "End after two consecutive turns with no progress, a repeated resolved ask, unsafe credential handling, or an incorrect terminal claim."

    scenario_db: dict[str, Any] = {
        "_current_date": "2026-08-19",
        "agent_variables": variables,
        "customer": customer,
        "evaluation": {
            "source_scenario_id": source["scenario_id"],
            "account_id": source["initial_environment"]["account_id"],
            "required_actions": required_tools,
            "accepted_dispositions": source["accepted_dispositions"],
            "forbidden_phrases": source["forbidden_phrases"],
        },
    }
    if acoustic:
        scenario_db["audio_perturbation"] = acoustic

    record = {
        "id": record_id,
        "current_date_time": "2026-08-19 16:30 IST",
        "user_goal": {
            "high_level_user_goal": f"You are Arnav, a busy and uninterested EMI customer. {source['user_goal']}. Follow the hidden behavior policy and do not help the agent succeed unless its behavior earns the scripted outcome.",
            "decision_tree": {
                "must_have_criteria": must_have,
                "nice_to_have_criteria": nice_to_have,
                "negotiation_behavior": behavior,
                "resolution_condition": resolution,
                "failure_condition": failure,
                "escalation_behavior": "Follow only the scenario's expected escalation or refusal path; never invent a live-agent request.",
                "edge_cases": [
                    "Ask for one repeat if audio is unclear.",
                    "Correct a wrong company, amount, product, or date once.",
                    "Stay terse and do not become a cooperative benchmark narrator.",
                ],
            },
            "information_required": {
                "customer_name": "Arnav",
                "company": "EasyCredit",
                "product": "Samsung Smart TV",
                "outstanding_amount_rupees": source["visible_context"]["outstandingAmount"],
                "scenario_truth": source["hidden_state"]["user_script_truth"],
                "expected_outcome": expected_outcome,
            },
        },
        "user_config": {
            "name": "Arnav",
            "gender": "man",
            "user_persona_id": 2,
            "user_persona": "Busy, skeptical, terse, and low patience. Speak naturally in the scenario language, interrupt repetition, and do not volunteer benchmark answers.",
        },
        "scenario_context": {
            "premise": "A controlled fictional EasyCredit EMI recovery call for a Samsung Smart TV.",
            "category": source["failure_family"],
            "intents": [{"intent": source["user_goal"], "satisfiable": True}],
            "escalate_to_live_agent": expected_outcome == "escalation",
            "source_scenario_id": source["scenario_id"],
            "suite": "acoustic" if acoustic else "core",
            "audio_perturbation": acoustic,
        },
        "culture_overrides": {"en": {"first_name": "Arnav", "last_name": "", "phone": ""}},
        "romanized_culture_overrides": {"en": {"first_name": "Arnav", "last_name": ""}},
        "starting_utterances": {"en": steps[0]},
        "ground_truth": {
            "expected_scenario_db": {
                **scenario_db,
                "customer": expected_customer,
            }
        },
        "category": source["failure_family"],
    }
    return record, scenario_db


def main() -> None:
    sources = _load_sources()
    existing = json.loads(EVA_DATA.read_text(encoding="utf-8"))
    existing = [row for row in existing if not row["id"].startswith("EMI-VOICE-")]
    records: list[dict[str, Any]] = []
    created: list[dict[str, Any]] = []
    for index, source_id in enumerate(CORE_SOURCE_IDS, 1):
        record_id = f"EMI-VOICE-{index:03d}"
        record, scenario = _record(sources[source_id], record_id, None)
        records.append(record)
        path = EVA_SCENARIOS / f"{record_id}.json"
        path.write_text(json.dumps(scenario, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        created.append({"record_id": record_id, "source_id": source_id, "suite": "core", "scenario_path": str(path)})
    for offset, (source_id, acoustic) in enumerate(ACOUSTIC_CASES, len(CORE_SOURCE_IDS) + 1):
        record_id = f"EMI-VOICE-{offset:03d}"
        record, scenario = _record(sources[source_id], record_id, acoustic)
        records.append(record)
        path = EVA_SCENARIOS / f"{record_id}.json"
        path.write_text(json.dumps(scenario, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        created.append({"record_id": record_id, "source_id": source_id, "suite": "acoustic", "perturbation": acoustic, "scenario_path": str(path)})

    EVA_DATA.write_text(json.dumps(existing + records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "eva-emi-voice-suite.v1",
        "status": "frozen_before_matched_live_execution",
        "records": created,
        "core_count": len(CORE_SOURCE_IDS),
        "acoustic_count": len(ACOUSTIC_CASES),
        "dataset_path": str(EVA_DATA),
        "dataset_sha256": _sha(EVA_DATA),
        "source_files": {
            name: _sha(SOURCE_ROOT / name)
            for name in ("development.jsonl", "validation.jsonl", "regression.jsonl")
        },
        "claim_boundary": "Prospective matched live suite. No result exists until both frozen Indus versions run identical record IDs and trial counts.",
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"dataset_sha256": manifest["dataset_sha256"], "records": len(records)}, indent=2))


if __name__ == "__main__":
    main()
