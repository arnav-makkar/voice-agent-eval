#!/bin/bash
# Everything that must be true before the S7 voice round, and nothing that spends.
# Prints the exact run commands at the end; placing the calls stays a human act.
cd "$(dirname "$0")/.."
PY=.venv/bin/python
ok(){ printf "  \033[32mOK \033[0m %s\n" "$1"; }
bad(){ printf "  \033[31mBAD\033[0m %s\n" "$1"; FAIL=1; }
FAIL=0
echo "=== S7 PREFLIGHT — bot-to-bot on the champion ==="

$PY - <<'EOF' && ok "champion intact on the committed agent" || bad "champion text drifted"
import sys, json, hashlib, time; sys.path.insert(0,'.')
from pathlib import Path
from framework.evaluation.adapters import indus_authoring as A
from scripts.gepa_optimize import assemble
want = assemble(json.loads(Path('artifacts/campaign2/improvement/CHAMPION.json').read_text()))
for _ in range(5):
    try:
        live = A.read_instructions(); break
    except Exception: time.sleep(10)
else: raise SystemExit(1)
h=lambda s: hashlib.sha256(s.strip().encode()).hexdigest()[:16]
print(f"       sha {h(live)} ({len(live)} chars)")
raise SystemExit(0 if h(live)==h(want) else 1)
EOF

grep -q '^SARVAM_APP_VERSION=4$' .env && ok "harness points at v4" || bad "SARVAM_APP_VERSION is not 4"

$PY - <<'EOF' && ok "agent clock is today's" || bad "agent clock stale"
import sys; sys.path.insert(0,'.')
from framework.evaluation.adapters import indus_authoring as A
print("      ", A.assert_clock_fresh())
EOF

code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 https://despite-gtk-checked-knit.trycloudflare.com/health)
[ "$code" = "200" ] && ok "tunnel 200 (tools reachable from Sarvam)" || bad "tunnel $code"
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8788/health)
[ "$code" = "200" ] && ok "tool service 200" || bad "tool service $code"

$PY - <<'EOF' && ok "the 5 EVA records are valid for today" || bad "an EVA record is stale"
import json, sys
from datetime import date
rows=json.load(open('research/upstream/eva/data/emi_dataset.json'))
want={"EMI-BENCH-0001","EMI-VOICE-002","EMI-VOICE-003","EMI-VOICE-004","EMI-VOICE-005"}
today=date.today().strftime("%d-%m-%Y")
bad=[]
for r in rows:
    if r["id"] not in want: continue
    av=r["ground_truth"]["expected_scenario_db"]["agent_variables"]
    if av.get("outstandingAmount")!="4416" or av.get("merchantName")!="EasyCredit": bad.append(r["id"]+":account")
    if not str(r.get("current_date_time","")).startswith("2026-08-23"): bad.append(r["id"]+":date")
print(f"       account pinned on all 5; current_date_time 2026-08-23; today is {today}")
sys.exit(1 if bad else 0)
EOF

$PY - <<'EOF' && ok "ElevenLabs caller configured" || bad "caller config wrong"
import os, sys; sys.path.insert(0,'scripts')
from dotenv import load_dotenv; load_dotenv('.env')
import provision_eva_elevenlabs_caller as P
key=os.getenv("ELEVENLABS_API_KEY","").strip()
g=P.request("GET","/v1/convai/agents/agent_5001m0cfkw7beaatc3d7abg4y7q6",key)["conversation_config"]
t,a=g["turn"],g["agent"]
print(f"       turn_timeout={t['turn_timeout']} eagerness={t.get('turn_eagerness')} "
      f"first_message={a['first_message']!r} llm={a['prompt']['llm']}")
sys.exit(0 if t["turn_timeout"]==2.0 and a["first_message"]=="" else 1)
EOF

echo
if [ "$FAIL" = "1" ]; then echo "  PREFLIGHT FAILED — fix the above before spending credits"; exit 1; fi
cat <<'CMDS'
  PREFLIGHT GREEN — nothing spent yet.

  The 5 bot-to-bot calls (~25 credits total, ~5 each):

    for r in EMI-BENCH-0001 EMI-VOICE-002 EMI-VOICE-003 EMI-VOICE-004 EMI-VOICE-005; do
      .venv/bin/python scripts/pilot_state.py reset 4416 $r EC-DEMO-$r
      perl -e 'alarm shift; exec @ARGV' 420 research/upstream/eva/.venv/bin/python \
        scripts/run_eva_samvaad_live.py --confirm-live --time-limit 120 --record-id $r
    done

  Then the 15 phone cards (yours to place, one at a time):

    .venv/bin/python scripts/place_phone_call.py --card N
CMDS
