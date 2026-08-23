"""Align the caller's known facts and each scenario's expected outcome.

Two mismatches this fixes:

1. The caller is given the account facts in user_goal.information_required, and
   those were never pinned. On EMI-VOICE-002 the caller spent three turns
   insisting the balance was Rs 2,950 against a correctly-pinned agent quoting
   4,416, which is what drove conversation_progression to 0.
2. EMI-VOICE-005's stated intent is "Dispute the purchase and stop recovery", so
   it is written here as a real dispute reaching record_dispute rather than the
   already-paid check it had been rewritten as.
"""
import json

DATASET = "research/upstream/eva/data/emi_dataset.json"
SEEDS = "research/upstream/eva/data/emi_scenarios"
AMOUNT, COMPANY = "4416", "EasyCredit"
LISTEN = "Let them finish speaking before you reply. Do not talk over them."

OUTCOME = {"EMI-VOICE-002": "fptp", "EMI-VOICE-003": "callback",
           "EMI-VOICE-004": "rtp",  "EMI-VOICE-005": "dispute"}

DISPUTE_CALLER = dict(
    goal=("Your phone rang and you picked up. You never bought this television and "
          "you believe someone has used your name for this loan. Say so clearly and "
          "ask them to raise a dispute and stop the recovery calls."),
    negotiation=[LISTEN,
                 "Say you never purchased this television and this loan is not yours.",
                 "Ask them to record a dispute and stop the collection calls.",
                 "Refuse to pay anything while the dispute is open."],
    resolution=("Wait until they tell you the dispute has been recorded. Then say "
                "goodbye."),
)

def main() -> int:
    recs = json.load(open(DATASET))
    for r in recs:
        rid = r["id"]
        if rid not in OUTCOME:
            continue

        if rid == "EMI-VOICE-005":
            g = r["user_goal"]
            g["high_level_user_goal"] = DISPUTE_CALLER["goal"]
            g["decision_tree"].update({
                "negotiation_behavior": DISPUTE_CALLER["negotiation"],
                "resolution_condition": DISPUTE_CALLER["resolution"],
            })

        info = r["user_goal"].get("information_required")
        if isinstance(info, dict):
            info["outstanding_amount_rupees"] = AMOUNT
            info["company"] = COMPANY
            info["expected_outcome"] = OUTCOME[rid]

        esd = r["ground_truth"]["expected_scenario_db"]
        if rid == "EMI-VOICE-005":
            esd["customer"]["outcome"] = "dispute"
            esd["evaluation"]["accepted_dispositions"] = ["dispute"]
            esd["evaluation"]["required_actions"] = [{"name": "record_dispute", "arguments": {}}]
            seed = json.load(open(f"{SEEDS}/{rid}.json"))
            seed["evaluation"]["accepted_dispositions"] = ["dispute"]
            seed["evaluation"]["required_actions"] = [{"name": "record_dispute", "arguments": {}}]
            json.dump(seed, open(f"{SEEDS}/{rid}.json", "w"), ensure_ascii=False, indent=2)

        print(f"  {rid:16} amount={info['outstanding_amount_rupees']} outcome={OUTCOME[rid]}")

    json.dump(recs, open(DATASET, "w"), ensure_ascii=False, indent=2)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
