"""Ring your phone from the campaign-2 agent, with one card's account loaded.

This is the S4 path: you answer, improvise from the card, and hang up. The card
fixes the situation, not the words. Every call is bound to its own ledger row
through campaignId, so the tool writes it produces can be checked against the
append-only journal afterwards rather than taken on trust.

    python scripts/place_phone_call.py --card 2
    python scripts/place_phone_call.py --card 2 --dry-run
    python scripts/place_phone_call.py --list

Cards live in agent/campaign2/CALL-CARDS.md. The account behind each call is a
real benchmark scenario, so the amounts and dates are internally consistent and
the agent can answer questions about any of them.
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

import certifi

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "artifacts" / "framework" / "emi" / "benchmark_v1" / "development.jsonl"
OUTBOUND = "https://apps.sarvam.ai/api/outbounds/v1/orgs/{org}/workspaces/{ws}/outbounds"
TOOL_SERVICE = os.getenv("AGENT_TOOL_BASE_URL", "http://127.0.0.1:8788")

# The agent declares exactly these. The outbound API rejects the whole call with a
# 422 if the payload carries anything else, and scenario context legitimately holds
# extras the agent never needed — nearFutureDate and cutoffDate are for the caller
# and the evaluator, not for the agent to speak.
AGENT_VARIABLES = frozenset({
    "amountPaidToDate", "balanceRemaining", "campaignId", "currentDate",
    "customerCareNumber", "daysOverdue", "downPayment", "dueDate", "emiNumber",
    "emisPaid", "emisRemaining", "financedAmount", "fraudHelplineNumber",
    "lateChargeAmount", "merchantName", "monthlyEmiAmount", "outstandingAmount",
    "productName", "productPrice", "purchaseDate", "tenureMonths", "tomorrowDate",
    "transactionReference", "userName",
})


# Each card is answered by a real scenario family, so the ledger the agent reads
# matches the situation you are playing.
CARD_FAMILY: dict[int, str] = {
    1: "pay_now_direct",
    2: "future_promise",
    3: "today_promise",
    4: "callback_capture",
    5: "already_paid",
    6: "dispute_handling",
    7: "explicit_refusal",
    8: "wrong_party_privacy",
    9: "credential_guardrail",
    10: "channel_unavailable",
    11: "fraud_escalation",
    12: "safety_escalation",
    13: "amount_question",
    14: "conditional_promise_trap",
    15: "ledger_interrogation",
}


def _env(*names: str) -> dict[str, str]:
    load_env(ROOT / ".env")
    values = {n: os.getenv(n, "").strip().strip('"').strip("'") for n in names}
    missing = [n for n, v in values.items() if not v]
    if missing:
        raise SystemExit(f"Missing from .env: {', '.join(missing)}")
    return values


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _request(method: str, url: str, headers: dict[str, str], payload: dict | None = None) -> dict:
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    ctx = ssl.create_default_context(cafile=certifi.where())
    try:
        with urllib.request.urlopen(req, timeout=45, context=ctx) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')[:600]}") from exc


def scenario_for(card: int) -> dict:
    family = CARD_FAMILY[card]
    rows = [json.loads(l) for l in BENCH.read_text(encoding="utf-8").splitlines() if l.strip()]
    hits = [r for r in rows if r["failure_family"] == family and r["language"] in {"hindi", "hinglish"}]
    if not hits:
        raise SystemExit(f"No Hindi/Hinglish scenario for family {family}")
    return hits[0]


def seed_ledger(run_id: str, account_id: str, outstanding: str, secret: str) -> None:
    """Give this call its own ledger row, clean, whether or not it has been used.

    Seeding refuses to overwrite an existing run, which is the right default for a
    measured campaign but wrong for a card you are redialling after a dropped
    line. Reset the row instead so a retry starts from the same blank state the
    first attempt did, with no tool writes carried over.
    """
    sys.path.insert(0, str(ROOT / "scripts"))
    from pilot_state import reset

    reset(outstanding, run_id, account_id)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--card", type=int, choices=sorted(CARD_FAMILY), help="Which call card to run.")
    parser.add_argument("--to", help="Number to ring. Defaults to SARVAM_TEST_USER_PHONE_NUMBER.")
    parser.add_argument("--list", action="store_true", help="Show the cards and their families.")
    parser.add_argument("--dry-run", action="store_true", help="Print the request; place no call.")
    args = parser.parse_args()

    if args.list:
        for n, fam in sorted(CARD_FAMILY.items()):
            print(f"  {n:>2}  {fam}")
        return 0
    if not args.card:
        parser.error("--card is required (or use --list)")

    env = _env(
        "SARVAM_VOICE_AGENTS_API_KEY", "SARVAM_ORG_ID", "SARVAM_WORKSPACE_ID",
        "SARVAM_APP_ID", "SARVAM_APP_VERSION", "SARVAM_CONNECTION_ID",
        "SARVAM_AGENT_PHONE_NUMBER", "AGENT_TOOL_SECRET",
    )
    to_number = args.to or os.getenv("SARVAM_TEST_USER_PHONE_NUMBER", "").strip().strip('"')
    if not to_number:
        raise SystemExit("No destination number: pass --to or set SARVAM_TEST_USER_PHONE_NUMBER")

    scenario = scenario_for(args.card)
    ctx = dict(scenario["visible_context"])
    # The ledger key carries the agent version. Seeding a run deletes that key's
    # existing events, so an unversioned key would erase the v3 baseline rows the
    # moment a v4 call is placed — and, worse, a half-reset key would blend two
    # versions' writes into one indistinguishable journal.
    run_id = f"c2-phone-{args.card:02d}-v{env['SARVAM_APP_VERSION']}"
    ctx["campaignId"] = run_id
    ctx["transactionReference"] = f"EC-PHONE-{args.card:02d}"
    # The scenario pins the calendar it was authored against. Sending that pinned
    # date to a call placed today hands the agent a clock that disagrees with the
    # real one, and every date it then speaks is graded against a different day —
    # the failure that once scored correct callback handling as a miss. The real
    # calendar wins at dial time; the scenario keeps everything else.
    from datetime import date as _date, timedelta as _td
    _today = _date.today()
    _clock = {
        "currentDate": _today.strftime("%d-%m-%Y"),
        "tomorrowDate": (_today + _td(days=1)).strftime("%d-%m-%Y"),
        "nearFutureDate": (_today + _td(days=3)).strftime("%d-%m-%Y"),
        "cutoffDate": (_today + _td(days=5)).strftime("%d-%m-%Y"),
    }
    _stale = {k: (ctx.get(k), v) for k, v in _clock.items()
              if k in ctx and str(ctx[k]) != v}
    ctx.update(_clock)

    variables = {k: str(v) for k, v in ctx.items() if k in AGENT_VARIABLES}
    dropped = sorted(set(ctx) - AGENT_VARIABLES - {"payment_status"})
    missing = sorted(AGENT_VARIABLES - set(variables))
    if missing:
        raise SystemExit(f"Scenario is missing agent variables: {', '.join(missing)}")

    payload = {
        "app_config": {
            "app_id": env["SARVAM_APP_ID"],
            "app_version": int(env["SARVAM_APP_VERSION"]),
            "app_type": "agent",
            "connection_config": {
                "connection_id": env["SARVAM_CONNECTION_ID"],
                "agent_phone_number": env["SARVAM_AGENT_PHONE_NUMBER"],
            },
            "agent_variables": variables,
        },
        "user_config": {"user_phone_number": to_number},
    }

    print(f"card {args.card} · {CARD_FAMILY[args.card]} · {scenario['scenario_id']}")
    print(f"  customer     {ctx['userName']}, Rs {ctx['outstandingAmount']} overdue on a {ctx['productName']}")
    print(f"  today is     {ctx['currentDate']}  (instalment {ctx['emiNumber']} of {ctx['tenureMonths']})")
    # Cards 2, 3 and 4 need a date said aloud. Print the exact one so the promise
    # you make and the date the evaluator expects can never drift apart.
    if args.card in {2, 3, 4}:
        wanted = {
            2: ("future date to name", ctx["nearFutureDate"]),
            3: ("say TODAY's date", ctx["currentDate"]),
            4: ("callback tomorrow", ctx["tomorrowDate"]),
        }[args.card]
        print(f"  SAY THIS DATE  {wanted[1]}   ({wanted[0]})")
    for _k, (_was, _now) in _stale.items():
        print(f"  clock fixed  {_k}: scenario pinned {_was} -> dialling with {_now}")
    print(f"  ledger row   {run_id}")
    if dropped:
        print(f"  not sent     {', '.join(dropped)}  (scenario-only, agent does not declare them)")
    print(f"  calling      {to_number} from {env['SARVAM_AGENT_PHONE_NUMBER']}  (agent v{env['SARVAM_APP_VERSION']})")

    if args.dry_run:
        print("\n--dry-run: no call placed, no ledger seeded.")
        return 0

    seed_ledger(run_id, ctx["transactionReference"], ctx["outstandingAmount"], env["AGENT_TOOL_SECRET"])
    url = OUTBOUND.format(org=env["SARVAM_ORG_ID"], ws=env["SARVAM_WORKSPACE_ID"])
    result = _request("POST", url,
                      {"Content-Type": "application/json", "X-API-Key": env["SARVAM_VOICE_AGENTS_API_KEY"]},
                      payload)
    print(f"\n  placed: {json.dumps(result, ensure_ascii=False)[:300]}")
    print(f"\nAfter the call:  python scripts/pilot_state.py read  (or check run {run_id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
