"""Pin the four bot-to-bot demo records to the deployed agent's account.

Two defects these records carried:

1. They used their own invented ledger (merchant "Croma", emi_amount 2950, no
   monthlyEmiAmount) instead of the account the live Indus agent is configured
   with. Every scenario must quote the same numbers the deployed agent quotes.
2. Their expected final database still encoded the *old* caller script, so a run
   of the rewritten caller scored task_completion 0 for doing the right thing —
   EMI-VOICE-002 expected a promise date of 20-08-2026 while the caller now says
   28 August.

Expectations below are derived from what each scenario demands, not from what any
run produced.
"""
import json

PATH = "research/upstream/eva/data/emi_dataset.json"
PINNED_FROM = "EMI-BENCH-0001"       # already pinned to the deployed account
KEEP_PER_RECORD = ("campaignId", "transactionReference")

CUSTOMER_BASE = {
    "name": "Arnav",
    "product": "Samsung Smart TV",
    "merchant": "EasyCredit",
    "emi_amount": "4416",
    "payment_status": "unpaid",
}

EXPECTED = {
    "EMI-VOICE-002": {"outcome": "fptp",         "promise_to_pay_date": "28-08-2026", "callback_at": None},
    "EMI-VOICE-003": {"outcome": "callback",     "promise_to_pay_date": None,
                      "callback_at": {"date": "24-08-2026", "time_window": "morning"}},
    "EMI-VOICE-004": {"outcome": "rtp",          "promise_to_pay_date": None, "callback_at": None},
    "EMI-VOICE-005": {"outcome": "acknowledged", "promise_to_pay_date": None, "callback_at": None},
}

def main() -> int:
    d = json.load(open(PATH))
    recs = d if isinstance(d, list) else d.get("records") or d.get("data")
    donor = next(r for r in recs if r["id"] == PINNED_FROM)
    account = donor["ground_truth"]["expected_scenario_db"]["agent_variables"]

    for r in recs:
        exp = EXPECTED.get(r["id"])
        if not exp:
            continue
        esd = r["ground_truth"]["expected_scenario_db"]
        own = {k: esd["agent_variables"].get(k) for k in KEEP_PER_RECORD}
        esd["agent_variables"] = {**account, **own}
        esd["customer"] = {**CUSTOMER_BASE, **exp}
        print(f"  {r['id']:16} outcome={exp['outcome']:14} "
              f"amount={esd['agent_variables']['outstandingAmount']} "
              f"merchant={esd['agent_variables']['merchantName']}")

    json.dump(d, open(PATH, "w"), ensure_ascii=False, indent=2)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
