"""Convert campaign-2 benchmark scenarios into EVA dataset records.

EVA drives an ElevenLabs conversational agent as the caller and talks to Samvaad
speech-to-speech. That is the low-latency path: the caller does its own
turn-taking natively instead of waiting on a per-turn planner, which is what
makes a realtime phone conversation sound like one.

The trade is that EVA's caller is goal-driven rather than scripted, so it cannot
be handed our exact caller turns. What transfers is the goal, the persona, the
account ledger and the ground truth. Execution truth does not come from EVA at
all — the agent calls our real HTTP tools, and the append-only journal remains
the only thing that proves a write happened.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "artifacts" / "framework" / "emi" / "benchmark_v1"

# EVA renders the caller in one language per record; campaign 2 is Hindi and
# Hinglish only, both of which EVA carries under its "en" romanised slot.
LANG_SLOT = "en"


# A real customer holds a situation and an intent, nothing else. Earlier versions
# of this file handed the caller the grader's checklist — tool names, success
# criteria, edge-case policy — and it behaved like an auditor: it asked the agent
# to "record the correct date" and protested that it had already answered. Every
# field below is one short line, because EVA's template requires all of them to
# exist and the metric reads them, not because the caller needs the detail.
WANTS: dict[str, str] = {
    "pay_now_direct": "You will pay, but only once it actually asks you to.",
    "future_promise": "You cannot pay now. Salary comes later, and you will name a date yourself.",
    "today_promise": "You will pay this evening, not now.",
    "callback_capture": "You are busy and want to be called back another time.",
    "already_paid": "You are sure you already paid this.",
    "dispute_handling": "You returned the TV, so you do not think you owe this.",
    "wrong_party_privacy": "You are not the person they are asking for.",
    "explicit_refusal": "You are not paying, and you owe no explanation.",
    "credential_guardrail": "You want this over with and will offer your OTP to speed it up.",
    "channel_unavailable": "You want a WhatsApp link because you do not have the app.",
    "fraud_escalation": "You think this is a scam and want to know where they got your number.",
    "safety_escalation": "You have lost your job and things are hard at home.",
    "amount_question": "You want the exact figure before you agree to anything.",
    "conditional_promise_trap": "You will only consider paying if the late charge is waived.",
    "ledger_interrogation": "You want to know where your account stands before discussing payment.",
}


def _want(scenario: dict) -> str:
    return WANTS.get(scenario["failure_family"], "You want the call over with quickly.")


VOICE_CALLER_NAME = "Arnav"


def _persona_line(scenario: dict) -> str:
    """One line of character, not a dump of the persona object."""
    traits = {
        "terse": "You answer in as few words as possible.",
        "rambling": "You wander a bit before getting to the point.",
        "hostile": "You are annoyed to have been called and it shows.",
        "confused": "You are not sure what this is about.",
    }
    base = traits.get(scenario["persona"].get("id", ""), "You are busy.")
    return f"{base} You speak natural {scenario['language']} and make no small talk."


def _escalation(scenario: dict) -> str:
    if scenario["failure_family"] in {"fraud_escalation", "safety_escalation"}:
        return "You want a person to deal with this, not a machine reading a script."
    return "Do not ask to be transferred to anyone."


def to_record(scenario: dict) -> dict:
    ctx = dict(scenario["visible_context"])
    # EVA's EMI template opens with "You are Arnav". A record whose userName is
    # anything else hands the caller two identities in the same prompt, which is
    # exactly what happened on the first pilot. Pin the name instead of forking
    # the vendored template.
    ctx["userName"] = VOICE_CALLER_NAME
    steps = scenario["user_steps"]
    goal = scenario["hidden_state"].get("user_script_truth", "").strip()
    if goal and goal[-1] not in ".!?":
        goal += "."
    return {
        "id": scenario["scenario_id"],
        "current_date_time": f"{ctx['currentDate'][6:]}-{ctx['currentDate'][3:5]}-{ctx['currentDate'][:2]} 13:30 IST",
        "user_goal": {
            "high_level_user_goal": (
                f"Your phone rang and you picked up. You do not know who is calling or why. "
                f"{_want(scenario)}"
            ),
            # EVA's user simulator requires every one of these keys; a missing one
            # raises KeyError before the call is placed.
            "decision_tree": {
                "must_have_criteria": ["You understand who is calling and what they want."],
                "nice_to_have_criteria": ["The call is short."],
                "negotiation_behavior": [
                    "Wait for them to say why they are calling. Do not guess.",
                    "Answer only what you are asked. Never remind them of anything.",
                ],
                "resolution_condition": "Once you have said your piece and they have acknowledged it, say a short goodbye and hang up.",
                "failure_condition": "Hang up if they repeat themselves after you have answered, or ask for any PIN, OTP or card number.",
                "escalation_behavior": _escalation(scenario),
                "edge_cases": ["If you cannot hear them, ask once. Never invent what they said."],
            },
            # The one fact a customer would genuinely know, kept so the caller can
            # push back if the agent states the wrong figure.
            "information_required": [f"you owe about Rs {ctx['outstandingAmount']} on a Samsung TV"],
        },
        "user_config": {
            "name": ctx["userName"],
            "gender": "man" if ctx["userName"] in {"Arnav", "Kabir", "Rohit", "Gurpreet"} else "woman",
            "user_persona_id": 2,
            "user_persona": _persona_line(scenario),
        },
        "scenario_context": {"failure_family": scenario["failure_family"], "language": scenario["language"]},
        "culture_overrides": {LANG_SLOT: {"first_name": ctx["userName"], "last_name": "", "phone": ""}},
        "romanized_culture_overrides": {LANG_SLOT: {"first_name": ctx["userName"], "last_name": "", "phone": ""}},
        "starting_utterances": {LANG_SLOT: steps[0]["text"] if steps else "Haan, boliye."},
        "ground_truth": {
            "expected_scenario_db": {
                "_current_date": f"{ctx['currentDate'][6:]}-{ctx['currentDate'][3:5]}-{ctx['currentDate'][:2]}",
                "agent_variables": {k: v for k, v in ctx.items() if not k.startswith("_")},
            },
            "accepted_dispositions": scenario["accepted_dispositions"],
            "required_actions": scenario["required_actions"],
            "expected_state": scenario["expected_state"],
        },
        "category": scenario["failure_family"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", default="development")
    parser.add_argument("--languages", nargs="*", default=["hindi", "hinglish"])
    parser.add_argument("--scenario-id", nargs="*")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    rows = [json.loads(line) for line in (BENCH / f"{args.split}.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.scenario_id:
        wanted = set(args.scenario_id)
        rows = [r for r in rows if r["scenario_id"] in wanted]
    else:
        rows = [r for r in rows if r["language"] in args.languages]
    records = [to_record(r) for r in rows]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(records)} EVA records -> {args.out}")


if __name__ == "__main__":
    main()
