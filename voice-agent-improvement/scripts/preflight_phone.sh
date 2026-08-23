#!/bin/bash
# Everything that must be true before a phone call is worth placing.
#
# Each check answers one question that has already cost a run:
#   1. prompt   — is the deployed agent v4, byte for byte? (.env once said 3)
#   2. clock    — is the agent's calendar today's? (a stale date scored correct
#                 callback handling as failure)
#   3. tunnel   — is the tool service up? (a dead tunnel looked exactly like an
#                 agent that chose not to call tools)
#   4. secret   — does the tool gate accept our key? (401s look like refusals)
#   5. e2e      — does a real turn from the deployed agent reach the journal?
#                 This is the only check that proves the whole path, because the
#                 agent's tool URL lives in a workspace registry we do not read.
#
# Exit non-zero on any failure. Placing a call on a red preflight burns credits
# and produces evidence you cannot trust.
set -uo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
fail=0
say(){ printf "  %-9s %s\n" "$1" "$2"; }

echo "=== preflight: phone tier on v4 ==="
$PY - <<'EOF'
import os, sys, json, hashlib, httpx
sys.path.insert(0, ".")
from dotenv import load_dotenv; load_dotenv(".env")
from framework.evaluation.adapters import indus_authoring as A

bad = 0
# 1. the deployed prompt is the committed champion
live = A.read_instructions()
sha  = hashlib.sha256(live.encode()).hexdigest()[:16]
want = json.load(open("artifacts/campaign2/v4_champion.json"))["sha"] \
       if os.path.exists("artifacts/campaign2/v4_champion.json") else None
print(f"  prompt    {len(live):,} chars  sha {sha}"
      + (f"  expected {want}" if want else "  (no pinned sha on file)"))
if want and sha != want:
    print("            MISMATCH — the deployed agent is not the committed champion"); bad = 1

# 2. the agent's clock is today's
try:
    dates = A.assert_clock_fresh()
    print(f"  clock     {dates.get('currentDate')}  (fresh)")
except Exception as e:
    print(f"  clock     STALE — {e}"); bad = 1

# 3+4. the tool service is reachable *and* accepts our secret
base   = os.environ["LOOPLINE_TOOL_BASE_URL"].rstrip("/")
secret = os.environ["LOOPLINE_TOOL_SECRET"]
try:
    r = httpx.get(f"{base}/health", timeout=25)
    print(f"  tunnel    {base}  HTTP {r.status_code}")
    if r.status_code != 200: bad = 1
except Exception as e:
    print(f"  tunnel    UNREACHABLE — {e}"); bad = 1

try:
    r = httpx.post(f"{base}/v1/tools/record-call-outcome",
                   headers={"X-Loopline-Tool-Key": secret},
                   json={"run_id": "PREFLIGHT", "account_id": "PREFLIGHT",
                         "disposition": "preflight"}, timeout=25)
    # 401 is a rejected key; 422 means the key passed and only the body was thin
    ok = r.status_code in (200, 422)
    print(f"  secret    HTTP {r.status_code}  {'accepted' if ok else 'REJECTED'}")
    if not ok: bad = 1
except Exception as e:
    print(f"  secret    FAILED — {e}"); bad = 1
sys.exit(bad)
EOF
[ $? -ne 0 ] && fail=1

# 5. end-to-end: a real turn from the deployed agent must land in the journal
$PY - <<'EOF'
import sys, json, time, subprocess
sys.path.insert(0, ".")
from dotenv import load_dotenv; load_dotenv(".env")
from framework.evaluation.adapters.indus_text_chat import ChatSession, load_token
from framework.evaluation.adapters import indus_authoring as A

RUN = A.stored_agent_variables()["campaignId"]  # text-chat ignores per-request
                                                # variables; probe the key the
                                                # runtime actually writes under
subprocess.run([".venv/bin/python", "scripts/pilot_state.py", "reset", "4416", RUN,
                "EC-PREFLIGHT"], capture_output=True)
try:
    s = ChatSession(app_version=int(__import__("os").getenv("SARVAM_APP_VERSION", "4")),
                    variables={}, token=load_token())
    s.start("नमस्ते")
    for line in ("हाँ मैं Arnav बोल रहा हूँ।",
                 "मैं आज ही पूरा payment कर दूँगा।",
                 "ठीक है धन्यवाद, रखता हूँ।"):
        s.say(line); time.sleep(1)
    time.sleep(3)
    j = json.loads(subprocess.run([".venv/bin/python", "scripts/pilot_state.py", "journal", RUN],
                                  capture_output=True, text=True).stdout or "{}")
    wrote = [e["tool"] for e in j.get("events", [])]
    print(f"  e2e       attempted {s.attempted_tools()}")
    print(f"  e2e       journal   {wrote or '(EMPTY — tools never reached the ledger)'}")
    sys.exit(0 if wrote else 1)
finally:
    pass
EOF
[ $? -ne 0 ] && fail=1

echo
if [ $fail -eq 0 ]; then echo "  ALL GREEN — safe to place calls"; else echo "  RED — fix the above before dialling"; fi
exit $fail
