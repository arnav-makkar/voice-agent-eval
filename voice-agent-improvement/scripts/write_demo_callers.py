"""Rewrite the four bot-to-bot demo callers in the clean style.

The originals told the caller to open with a scripted line and to withhold
cooperation until the agent "earned" it. The scripted opener lands ~1.9s late
after TTS and collides with Shubh's greeting, and the adversarial framing pushed
the caller into talking over him. These are written instead as a person with a
situation, with one rule that matters for turn-taking: let the other side finish.

Each caller also waits for Shubh to say what he has recorded before hanging up,
so an end-of-call tool has a turn in which to fire.
"""
import json

PATH = "research/upstream/eva/data/emi_dataset.json"
LISTEN = "Let them finish speaking before you reply. Do not talk over them."

CALLERS = {
    "EMI-VOICE-002": dict(
        goal=("Your phone rang and you picked up. You do not know who is calling. "
              "You intend to pay but you have no money until your salary arrives on "
              "28 August. When they ask when you can pay, say 28 August. Do not "
              "offer any other date."),
        negotiation=[LISTEN,
                     "Say you cannot pay today because you have no money right now.",
                     "When asked for a date, say 28 August. Repeat it once if misheard.",
                     "Do not agree to pay today, however they press."],
        resolution=("Wait until they tell you what date they have noted down. Then "
                    "say thank you and goodbye."),
    ),
    "EMI-VOICE-003": dict(
        goal=("Your phone rang and you picked up. You are driving and cannot talk "
              "now. Ask them to call you back tomorrow morning."),
        negotiation=[LISTEN,
                     "Say you are driving and cannot talk right now.",
                     "Ask them to call back tomorrow morning.",
                     "Do not discuss the amount and do not commit to paying on this call."],
        resolution=("Wait until they confirm the callback is booked. Then say thanks "
                    "and goodbye."),
    ),
    "EMI-VOICE-004": dict(
        goal=("Your phone rang and you picked up. You are not going to pay this "
              "month and you have decided that firmly. Say so plainly."),
        negotiation=[LISTEN,
                     "Say clearly that you will not pay this month.",
                     "Do not give a date and do not agree to a callback.",
                     "Stay polite but do not soften your position."],
        resolution=("Wait until they tell you what they have recorded about your "
                    "refusal. Then say goodbye."),
    ),
    "EMI-VOICE-005": dict(
        goal=("Your phone rang and you picked up. You believe you already paid this "
              "month and you want them to check before you discuss anything else."),
        negotiation=[LISTEN,
                     "Say you think you already paid and ask them to check the record.",
                     "If they answer from memory without checking, ask them to check properly, once.",
                     "Do not agree to pay until they tell you what the record shows."],
        resolution=("Wait until they tell you what the payment record actually shows. "
                    "Acknowledge it, then say goodbye."),
    ),
}

def main() -> int:
    d = json.load(open(PATH))
    recs = d if isinstance(d, list) else d.get("records") or d.get("data")
    for r in recs:
        spec = CALLERS.get(r["id"])
        if not spec:
            continue
        g = r["user_goal"]
        g["high_level_user_goal"] = spec["goal"]
        g["decision_tree"].update({
            "negotiation_behavior": spec["negotiation"],
            "resolution_condition": spec["resolution"],
        })
        # starting_utterances is left as-is: it is a dict the schema requires, and
        # the caller no longer speaks first because first_message is empty and the
        # forked system_prompt_emi no longer mandates the scripted opener.
        print(f"  {r['id']:16} {r.get('category')}")
    json.dump(d, open(PATH, "w"), ensure_ascii=False, indent=2)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
