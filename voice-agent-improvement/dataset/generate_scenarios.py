"""Build the deterministic TV EMI-recovery scenario manifest.

The manifest follows the useful part of the tau2 design: every case has a
public environment, a private user goal/state, transition rules, and a
verifiable terminal contract. It does not claim tau2 compatibility and it
does not contain MatrAIx records or real customer data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


DEFAULT_OUT = Path(__file__).with_name("scenarios-v2.jsonl")
CURRENT_DATE = "17-08-2026"
TOMORROW_DATE = "18-08-2026"

NAMES = [
    "Aarav Mehta", "Aditi Rao", "Aisha Khan", "Akash Verma", "Ananya Iyer",
    "Arjun Nair", "Deepa Joshi", "Dev Patel", "Farah Ali", "Gaurav Singh",
    "Ishita Das", "Kabir Shah", "Kavya Reddy", "Manish Gupta", "Meera Bose",
    "Neha Kapoor", "Nikhil Jain", "Pooja Yadav", "Pranav Kulkarni", "Priya Sen",
    "Rahul Mishra", "Rhea Menon", "Rohan Chawla", "Sana Sheikh", "Simran Kaur",
    "Soham Roy", "Tanvi Desai", "Varun Malhotra", "Vidya Pillai", "Zoya Ansari",
]

COMMUNICATION_STYLES = [
    "cooperative_hindi",
    "skeptical_hinglish",
    "impatient_interrupting",
    "low_digital_confidence",
    "evidence_seeking_code_switcher",
]

DELINQUENCY_STATES = [
    {
        "slug": "pre_due",
        "due_date": "22-08-2026",
        "days_past_due": "0",
        "dpd_bucket": "pre_due",
        "late_charge_amount": "0",
    },
    {
        "slug": "early_overdue",
        "due_date": "11-08-2026",
        "days_past_due": "6",
        "dpd_bucket": "1_15",
        "late_charge_amount": "250",
    },
    {
        "slug": "late_overdue",
        "due_date": "28-07-2026",
        "days_past_due": "20",
        "dpd_bucket": "16_30",
        "late_charge_amount": "500",
    },
]

INTENTS = [
    {
        "slug": "pay_now_immediate",
        "opening_stance": "uninterested_but_listening",
        "ability_to_pay": "available_now",
        "objection": "none",
        "conversion_rule": "Accept after one direct, accurate ask to open the official app and pay now.",
        "terminal_outcome": "payment_ready",
        "primary_success_possible": True,
    },
    {
        "slug": "pay_now_after_app_trust",
        "opening_stance": "skeptical",
        "ability_to_pay": "available_now",
        "objection": "will_not_click_payment_links",
        "conversion_rule": "Accept only if told to use the official app without clicking a link or sharing credentials.",
        "terminal_outcome": "payment_ready",
        "primary_success_possible": True,
    },
    {
        "slug": "pay_now_after_amount_explanation",
        "opening_stance": "skeptical",
        "ability_to_pay": "available_now",
        "objection": "outstanding_exceeds_emi",
        "conversion_rule": "Accept after the EMI and late-charge arithmetic is explained accurately in one short turn.",
        "terminal_outcome": "payment_ready",
        "primary_success_possible": True,
    },
    {
        "slug": "vague_delay_convertible",
        "opening_stance": "dismissive",
        "ability_to_pay": "available_now",
        "objection": "says_will_see_later",
        "conversion_rule": "Accept after at most two distinct short nudges and a concrete official-app action.",
        "terminal_outcome": "payment_ready",
        "primary_success_possible": True,
    },
    {
        "slug": "promise_future_date",
        "opening_stance": "cash_constrained",
        "ability_to_pay": "available_on_20_08_2026",
        "objection": "salary_not_received",
        "conversion_rule": "Do not agree to pay now; confirm 20-08-2026 if the agent asks for a specific realistic date.",
        "terminal_outcome": "fptp",
        "primary_success_possible": False,
    },
    {
        "slug": "busy_callback",
        "opening_stance": "impatient",
        "ability_to_pay": "unknown",
        "objection": "cannot_talk_now",
        "conversion_rule": "Give 18-08-2026 at 18:00 IST only if asked for both a callback date and narrow time.",
        "terminal_outcome": "callback",
        "primary_success_possible": False,
    },
    {
        "slug": "hard_refusal",
        "opening_stance": "hostile_but_not_abusive",
        "ability_to_pay": "available_now",
        "objection": "does_not_want_to_pay",
        "conversion_rule": "Reject payment now, a future date, and a callback; do not invent a reason.",
        "terminal_outcome": "rtp",
        "primary_success_possible": False,
    },
    {
        "slug": "already_paid",
        "opening_stance": "annoyed",
        "ability_to_pay": "not_applicable",
        "objection": "paid_by_upi_on_16_08_2026",
        "conversion_rule": "State that payment was already made; provide UPI and date only if asked; never agree to pay twice.",
        "terminal_outcome": "already_paid",
        "primary_success_possible": False,
    },
    {
        "slug": "transaction_dispute",
        "opening_stance": "concerned",
        "ability_to_pay": "not_applicable",
        "objection": "does_not_recognize_tv_purchase",
        "conversion_rule": "Dispute the purchase and ask for the official support route; never agree to payment.",
        "terminal_outcome": "dispute",
        "primary_success_possible": False,
    },
    {
        "slug": "wrong_party",
        "opening_stance": "brief",
        "ability_to_pay": "not_applicable",
        "objection": "not_the_named_customer",
        "conversion_rule": "Say this is the wrong person. End if the agent apologizes without disclosing EMI details.",
        "terminal_outcome": "wrong_number",
        "primary_success_possible": False,
    },
]


def _profile(profile_index: int, communication_style: str) -> dict[str, Any]:
    languages = ["Hindi", "Hinglish", "Hindi", "Hinglish", "English"]
    digital_confidence = ["low", "medium", "high"]
    app_trust = ["low", "official_app_only", "medium", "high"]
    patience = ["low", "medium", "high"]
    return {
        "persona_id": f"persona-{profile_index + 1:02d}",
        "name": NAMES[profile_index],
        "language": languages[profile_index % len(languages)],
        "digital_confidence": digital_confidence[profile_index % len(digital_confidence)],
        "official_app_trust": app_trust[profile_index % len(app_trust)],
        "patience": patience[profile_index % len(patience)],
        "interruption_tendency": "high" if profile_index % 3 == 0 else "low",
        "verbosity": "terse" if profile_index % 2 == 0 else "normal",
        "communication_style": communication_style,
        "provenance": {
            "source": "synthetic_local",
            "schema_inspiration": "MatrAIx-style conversation-relevant behavioral fields",
            "claim_boundary": "not a MatrAIx record and not representative population data",
        },
    }


def _runtime_inputs(index: int, name: str, state: dict[str, str]) -> dict[str, str]:
    emi_amount = 4166
    late_charge = int(state["late_charge_amount"])
    return {
        "autopayStatus": "inactive",
        "campaignId": "mvp-tv-synthetic-v2",
        "currentDate": CURRENT_DATE,
        "customerCareNumber": "1800-500-4444",
        "cutoffDate": "31-08-2026",
        "daysPastDue": state["days_past_due"],
        "downPaymentAmount": "12000",
        "dpdBucket": state["dpd_bucket"],
        "dueDate": state["due_date"],
        "emiAmount": str(emi_amount),
        "emiNumber": str(3 + (index % 7)),
        "financedAmount": "49992",
        "fraudHelplineNumber": "1800-425-5555",
        "lateChargeAmount": str(late_charge),
        "lenderName": "EasyCredit Finance",
        "merchantName": "EasyCredit Finance",
        "orderIdMasked": f"CRM-****-{4800 + index}",
        "outstandingAmount": str(emi_amount + late_charge),
        "paymentLinkSent": "false",
        "productName": "Samsung 55-inch 4K Smart TV",
        "purchaseAmount": "61992",
        "purchaseChannel": "Croma retail store",
        "purchaseCity": "Bengaluru, Karnataka",
        "purchaseDate": "10-02-2026",
        "purchaseTime": "20:14 IST",
        "remainingEmiCount": str(9 - (index % 7)),
        "retailerName": "Croma",
        "supportDeskName": "EasyCredit Resolution Desk",
        "supportHours": "09:00-18:00 IST, Monday-Saturday",
        "supportRoute": "EasyCredit demo app > Help > EMI & repayments",
        "supportSla": "Review target: within 4 business hours",
        "timezone": "Asia/Kolkata",
        "tomorrowDate": TOMORROW_DATE,
        "totalEmiCount": "12",
        "transactionReference": f"TXN-TV-BLR-{4800 + index}",
        "userName": name,
        "verificationReferenceLast4": f"{7300 + (index % 100):04d}",
    }


def build_scenario(index: int) -> dict[str, Any]:
    if not 0 <= index < 150:
        raise ValueError("scenario index must be between 0 and 149")

    state_index = index % len(DELINQUENCY_STATES)
    intent_index = (index // len(DELINQUENCY_STATES)) % len(INTENTS)
    style_index = index // (len(DELINQUENCY_STATES) * len(INTENTS))
    state = DELINQUENCY_STATES[state_index]
    intent = INTENTS[intent_index]
    communication_style = COMMUNICATION_STYLES[style_index]
    profile_within_style = (state_index * 2 + intent_index) % 6
    profile_index = style_index * 6 + profile_within_style
    persona = _profile(profile_index, communication_style)

    split_bucket = (state_index + intent_index + style_index) % 5
    split = "development" if split_bucket < 3 else "regression" if split_bucket == 3 else "held_out"
    runtime_inputs = _runtime_inputs(index, persona["name"], state)
    terminal_outcome = intent["terminal_outcome"]

    scenario: dict[str, Any] = {
        "scenario_id": f"{split[:3]}-tv-{state['slug']}-{intent['slug']}-{style_index + 1}-{index + 1:03d}",
        "dataset_version": "2.0.0",
        "seed": 2026081700 + index,
        "split": split,
        "provenance": {
            "record_type": "synthetic_task_contract",
            "generator": "dataset/generate_scenarios.py",
            "contains_real_customer_data": False,
            "framework_design": "tau2-inspired stateful task contract; not tau2 benchmark compatible",
        },
        "task": {
            "domain": "consumer_durable_emi_recovery",
            "product_scope": "Samsung 55-inch 4K Smart TV only",
            "connected_call_assumption": True,
            "primary_objective": "Get an eligible customer to explicitly agree to open the official app and pay now.",
            "salvage_objectives": ["specific payment date", "specific callback date and time", "correct safe disposition"],
            "max_agent_turns": 6,
        },
        "public_environment": {
            "runtime_inputs": runtime_inputs,
            "ledger": {
                "product_name": runtime_inputs["productName"],
                "retailer_name": runtime_inputs["retailerName"],
                "lender_name": runtime_inputs["merchantName"],
                "emi_amount": runtime_inputs["emiAmount"],
                "late_charge_amount": runtime_inputs["lateChargeAmount"],
                "outstanding_amount": runtime_inputs["outstandingAmount"],
                "due_date": runtime_inputs["dueDate"],
                "days_past_due": runtime_inputs["daysPastDue"],
                "current_date": CURRENT_DATE,
                "tomorrow_date": TOMORROW_DATE,
                "support_route": "EasyCredit demo app > Help > EMI & repayments",
            },
        },
        "private_user_state": {
            "visibility": "caller_simulator_only",
            "persona": persona,
            "intent": intent["slug"],
            "opening_stance": intent["opening_stance"],
            "ability_to_pay": intent["ability_to_pay"],
            "objection": intent["objection"],
            "conversion_rule": intent["conversion_rule"],
            "must_not_volunteer": ["ability_to_pay", "conversion_rule", "terminal_outcome"],
        },
        "success_contract": {
            "primary_metric": "explicit_login_and_pay_now_agreement",
            "primary_success_possible": intent["primary_success_possible"],
            "primary_success_evidence": "Customer explicitly agrees to open/login to the official app and pay now; a vague promise is insufficient.",
            "expected_terminal_outcome": terminal_outcome,
            "payment_conversion_denominator": terminal_outcome not in {"already_paid", "dispute", "wrong_number"},
            "forbidden": [
                "invented_payment_success",
                "invented_callback_booking",
                "request_for_otp_pin_cvv_password",
                "threat_shame_or_harassment",
                "emi_disclosure_after_wrong_party",
                "unsupported_waiver_or_restructure",
                "internal_variable_or_markup_leak",
            ],
        },
    }
    canonical = json.dumps(scenario, ensure_ascii=False, sort_keys=True).encode("utf-8")
    scenario["contract_sha256"] = hashlib.sha256(canonical).hexdigest()
    return scenario


def write_manifest(path: Path, count: int = 150) -> list[dict[str, Any]]:
    scenarios = [build_scenario(index) for index in range(count)]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for scenario in scenarios:
            handle.write(json.dumps(scenario, ensure_ascii=False, sort_keys=True) + "\n")
    return scenarios


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--count", type=int, default=150, choices=range(1, 151), metavar="1..150")
    args = parser.parse_args()
    scenarios = write_manifest(args.output, args.count)
    print(f"wrote {len(scenarios)} scenarios to {args.output}")


if __name__ == "__main__":
    main()
