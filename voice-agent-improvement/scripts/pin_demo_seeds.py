"""Pin the bot-to-bot demo seeds to the deployed agent's account.

data/emi_scenarios/<record>.json is what supplies the runtime variables sent to
Samvaad, so pinning data/emi_dataset.json alone was not enough: EMI-VOICE-002
still made Shubh quote Rs 2,950 from its own seed after the dataset said 4,416.

The voice seeds also carried the campaign-1 variable schema (emiAmount,
lenderName, retailerName, dpdBucket) rather than the 24 variables the deployed
v3 agent declares, so most of their values never bound to anything.

Expectations are set from what each scenario demands, not from any run's output.
"""
import copy, json
from pathlib import Path

SEEDS = Path("research/upstream/eva/data/emi_scenarios")
DATASET = Path("research/upstream/eva/data/emi_dataset.json")
DONOR = "EMI-BENCH-0001"

ACCOUNTS = {
    "EMI-VOICE-002": "EC-DEMO-2950",
    "EMI-VOICE-003": "EC-DEMO-2984",
    "EMI-VOICE-004": "EC-DEMO-3001",
    "EMI-VOICE-005": "EC-DEMO-3018",
}

CUSTOMER_BASE = {
    "name": "Arnav", "product": "Samsung Smart TV", "merchant": "EasyCredit",
    "emi_amount": "4416", "payment_status": "unpaid",
}

OUTCOMES = {
    "EMI-VOICE-002": {"outcome": "fptp",         "promise_to_pay_date": "28-08-2026", "callback_at": None},
    "EMI-VOICE-003": {"outcome": "callback",     "promise_to_pay_date": None,
                      "callback_at": {"date": "24-08-2026", "time_window": "morning"}},
    "EMI-VOICE-004": {"outcome": "rtp",          "promise_to_pay_date": None, "callback_at": None},
    "EMI-VOICE-005": {"outcome": "acknowledged", "promise_to_pay_date": None, "callback_at": None},
}

REQUIRED = {
    "EMI-VOICE-002": [{"name": "record_promise_to_pay", "arguments": {"date": "28-08-2026"}}],
    "EMI-VOICE-003": [{"name": "schedule_callback", "arguments": {"date": "24-08-2026"}}],
    "EMI-VOICE-004": [],
    "EMI-VOICE-005": [{"name": "check_payment_status", "arguments": {}}],
}

def main() -> int:
    donor = json.load(open(SEEDS / f"{DONOR}.json"))["agent_variables"]

    for rid, account in ACCOUNTS.items():
        variables = copy.deepcopy(donor)
        variables["campaignId"] = rid
        variables["transactionReference"] = account

        seed = json.load(open(SEEDS / f"{rid}.json"))
        seed["_current_date"] = "2026-08-23"
        seed["agent_variables"] = variables
        seed["customer"] = {**CUSTOMER_BASE, "outcome": None,
                            "promise_to_pay_date": None, "callback_at": None}
        seed["evaluation"]["account_id"] = account
        seed["evaluation"]["required_actions"] = REQUIRED[rid]
        seed["evaluation"]["accepted_dispositions"] = [OUTCOMES[rid]["outcome"]]
        json.dump(seed, open(SEEDS / f"{rid}.json", "w"), ensure_ascii=False, indent=2)

    records = json.load(open(DATASET))
    for r in records:
        rid = r["id"]
        if rid not in ACCOUNTS:
            continue
        esd = r["ground_truth"]["expected_scenario_db"]
        esd["_current_date"] = "2026-08-23"
        variables = copy.deepcopy(donor)
        variables["campaignId"] = rid
        variables["transactionReference"] = ACCOUNTS[rid]
        esd["agent_variables"] = variables
        esd["customer"] = {**CUSTOMER_BASE, **OUTCOMES[rid]}
        esd["evaluation"]["account_id"] = ACCOUNTS[rid]
        esd["evaluation"]["required_actions"] = REQUIRED[rid]
        esd["evaluation"]["accepted_dispositions"] = [OUTCOMES[rid]["outcome"]]
        print(f"  {rid:16} amount={variables['outstandingAmount']} "
              f"merchant={variables['merchantName']:11} outcome={OUTCOMES[rid]['outcome']}")
    json.dump(records, open(DATASET, "w"), ensure_ascii=False, indent=2)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
