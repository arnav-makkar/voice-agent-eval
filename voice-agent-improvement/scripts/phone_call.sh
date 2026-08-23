#!/bin/bash
# Score one phone card after you hang up.
#
#   bash scripts/preflight_phone.sh            # once, before the session
#   .venv/bin/python scripts/place_phone_call.py --card 3
#   ...take the call...
#   bash scripts/phone_call.sh 3               # read the ledger, score it
#
# Placing the call already seeds a ledger row keyed to this card (`c2-phone-NN`)
# and sends campaignId with the dial request, so each call has its own journal
# key and no timestamp windowing is needed to tell two calls apart. This script
# only reads that key back and checks it against the card's contract.
#
# The journal is the only evidence about tools. What the agent *said* it did
# never enters the verdict.
set -uo pipefail
cd "$(dirname "$0")/.."
CARD="${1:?usage: phone_call.sh CARD_NUMBER}"
.venv/bin/python - "$CARD" <<'EOF'
import os, sys, json, subprocess
sys.path.insert(0, ".")
from dotenv import load_dotenv; load_dotenv(".env")
card = sys.argv[1]
run  = f"c2-phone-{int(card):02d}-v{os.getenv('SARVAM_APP_VERSION','4')}"
spec = next(c for c in json.load(open("artifacts/campaign2/phone/baseline_15.json"))["per_card"]
            if str(c["card"]) == card)

j = json.loads(subprocess.run([".venv/bin/python", "scripts/pilot_state.py", "journal", run],
                              capture_output=True, text=True).stdout or "{}")
got     = [e["tool"] for e in j.get("events", [])]
seeded  = j.get("state") is not None
if not seeded:
    raise SystemExit(f"  card {card}: ledger {run} was never seeded — no call has been "
                     f"placed on this version yet. Run place_phone_call.py --card {card} first.")
if not got:
    print(f"  card {card}  ledger {run}")
    print( "  journal      EMPTY — the call left no tool writes.")
    print( "  This is a real result only if the preflight was green when you dialled;")
    print( "  otherwise it means the transport dropped. Re-run preflight, then re-dial.")
    print( "  Nothing saved. Re-run this once you are sure.")
    raise SystemExit(1)
need    = list(spec["required"]) + ["record_call_outcome"]
missing = [t for t in need if t not in got]
dupes   = {t: got.count(t) for t in set(got) if got.count(t) > 1}

# A missing write is only the agent's fault if the agent had the chance to make it.
#
# `record_call_outcome` is a *terminal* disposition: it records how the call ended,
# so it cannot be written defensively part-way through. Negotiation moves the
# outcome — a caller who opens with "I already paid" may end up promising to pay —
# and an early write would simply record the wrong thing. The agent therefore has
# no way to protect itself against a caller who hangs up mid-negotiation, and
# scoring that FAIL charges the agent for the tester's timing.
#
# The tell is the agent's last turn. Once it has delivered a closing line the
# outcome was settled enough to name — and the prompt supplies a code for every
# case, including `acknowledged` when the customer committed to nothing, so there
# is no ambiguity that excuses writing nothing. A closing line with no tool call is
# the say-vs-do defect: card 5 said "मैं आपका response note कर लेता हूँ" and wrote
# nothing. A last turn still mid-negotiation, cut off by the caller, is not.
CLOSING = ("धन्यवाद", "शुभ हो", "ख्याल रखिएगा", "note कर", "goodbye", "thank you")
closed, last_turn, end_reason = None, None, None
try:
    from scripts.call_context import last_call_context  # transcript + end_reason
    ctx = last_call_context(run)
    last_turn, end_reason = ctx.get("last_agent_turn"), ctx.get("end_reason")
    if last_turn is not None:
        closed = any(k.lower() in last_turn.lower() for k in CLOSING)
except Exception as exc:  # analytics lag or no network — fall back to strict
    print(f"  note         could not read call context ({str(exc)[:60]})")

inconclusive = bool(missing) and closed is False and end_reason == "USER_ENDS"
passed = not missing

print(f"  card {card}  {spec['family']}   ledger {run}")
print(f"  journal      {got or '(EMPTY — re-run preflight before trusting this)'}")
print(f"  required     {need}")
if end_reason:
    print(f"  ended by     {end_reason}")
if inconclusive:
    print(f"  verdict      INCONCLUSIVE — missing {', '.join(missing)}, but the caller hung up")
    print( "               mid-negotiation before the agent reached a closing. Not scored")
    print( "               against the agent; re-dial this card to get a verdict.")
elif missing and closed:
    print(f"  verdict      FAIL — missing {', '.join(missing)}")
    print(f"  say-vs-do    the agent delivered a closing and wrote nothing:")
    print(f"               \"{(last_turn or '')[:88]}\"")
else:
    print(f"  verdict      {'PASS' if passed else 'FAIL — missing ' + ', '.join(missing)}")
if dupes:
    print(f"  duplicates   {dupes}")
was = "PASS" if spec["passed"] else "FAIL"
tag = ("   <- FIXED" if passed and not spec["passed"] else
       "   <- REGRESSION" if spec["passed"] and not passed else "")
print(f"  v3 baseline  {was}{tag}")

out = f"artifacts/campaign2/phone/v4_card_{int(card):02d}.json"
json.dump({"card": int(card), "family": spec["family"], "run_id": run, "version": 4,
           "tools": got, "required": need, "missing": missing,
           "duplicates": dupes or None, "passed": passed,
           "exactly_once": not dupes, "v3_passed": spec["passed"]},
          open(out, "w"), indent=1)
print(f"  saved        {out}")
EOF
