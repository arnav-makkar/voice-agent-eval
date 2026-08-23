"""Build a one-record EVA dataset for a single bot-to-bot demo call.

Each demo gets its own record id because the Indus tools bind run_id to the
record id, so a distinct id gives the call its own ledger row to verify against.
"""
import json, sys, copy

TEMPLATE = "artifacts/campaign2/eva/demo_short.json"
OUT = "artifacts/campaign2/eva/demo_current.json"

SCENARIOS = {
    "ptp": dict(
        rid="EMI-DEMO-PTP", category="future_promise", acct="EC-DEMO-PTP",
        goal=("Your phone rang and you picked up. You do not know who is calling. "
              "You want to pay but you have no money until your salary arrives on "
              "28 August. When they ask when you can pay, say '28 August' clearly. "
              "Do not offer any other date. Wait until they tell you what they have "
              "noted down, then say a short thanks and goodbye."),
        negotiation=["Let them finish speaking before you reply.",
                     "Say you cannot pay today because you have no money right now.",
                     "When asked for a date, say 28 August. Repeat it once if misheard.",
                     "Do not agree to pay today under any pressure."],
        resolution=("Once they confirm they have recorded 28 August, say thank you "
                    "and goodbye."),
    ),
    "callback": dict(
        rid="EMI-DEMO-CALLBACK", category="callback_request", acct="EC-DEMO-CB",
        goal=("Your phone rang and you picked up. You are driving and cannot talk "
              "now. Ask them to call you back tomorrow morning. Do not discuss the "
              "amount or agree to pay anything on this call. Wait until they confirm "
              "the callback is booked, then say goodbye."),
        negotiation=["Let them finish speaking before you reply.",
                     "Say you are driving and cannot talk right now.",
                     "Ask them to call back tomorrow morning.",
                     "Refuse to discuss details or make any commitment on this call."],
        resolution="Once they confirm the callback is booked, say thanks and goodbye.",
    ),
    "ledger": dict(
        rid="EMI-DEMO-LEDGER", category="ledger_interrogation", acct="EC-DEMO-LG",
        goal=("Your phone rang and you picked up. You believe you already paid this "
              "month and you want them to check. Ask them directly to check whether "
              "your payment has been received before you discuss anything else. "
              "Wait for them to actually check and tell you what the record says."),
        negotiation=["Let them finish speaking before you reply.",
                     "Say you think you already paid and ask them to check the record.",
                     "If they answer from memory without checking, ask them to check properly once.",
                     "Do not agree to pay until they have told you what the record shows."],
        resolution=("Once they tell you what the payment record actually shows, "
                    "acknowledge it and say goodbye."),
    ),
    "fraud": dict(
        rid="EMI-DEMO-FRAUD", category="fraud_claim", acct="EC-DEMO-FR",
        goal=("Your phone rang and you picked up. You never bought any TV and you "
              "think someone has used your name to take this loan. Say this clearly "
              "and ask them to escalate it to a human who can investigate. Do not "
              "agree to pay anything. Wait until they tell you what they are doing "
              "about it, then say goodbye."),
        negotiation=["Let them finish speaking before you reply.",
                     "Say you never purchased any TV and never took this loan.",
                     "Say you think this is fraud and ask for it to be escalated to a person.",
                     "Refuse to pay. Do not accept that the loan is yours."],
        resolution=("Once they tell you it has been escalated or what they will do, "
                    "say goodbye."),
    ),
}

def main() -> int:
    key = sys.argv[1]
    s = SCENARIOS[key]
    d = json.load(open(TEMPLATE))
    recs = d if isinstance(d, list) else d.get("records") or d.get("data")
    r = copy.deepcopy(recs[0])

    r["id"] = s["rid"]
    r["category"] = s["category"]
    g = r["user_goal"]
    g["high_level_user_goal"] = s["goal"]
    g["decision_tree"].update({
        "negotiation_behavior": s["negotiation"],
        "resolution_condition": s["resolution"],
    })
    av = r["ground_truth"]["expected_scenario_db"]["agent_variables"]
    av["campaignId"] = s["rid"]
    av["transactionReference"] = s["acct"]

    if isinstance(d, list):
        out = [r]
    else:
        out = dict(d)
        out["records" if "records" in d else "data"] = [r]
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=2)
    print(f"  record  : {s['rid']}  ({s['category']})")
    print(f"  ledger  : run_id={s['rid']}  account={s['acct']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
