#!/bin/bash
# One bot-to-bot call, scored on what the agent actually said.
#
#   bash scripts/run_bot_call.sh EMI-VOICE-003
#
# EVA builds the judged conversation from user_simulator_events.jsonl, whose
# assistant_speech entries are the *caller's* speech-to-text applied to the
# agent's audio. Judging an agent through the other party's microphone charges
# its ASR errors to the agent: one call was penalised for "forgetting the
# customer's name" over a hallucinated "Thank you, Aruna ji. Hello, Deepak." that
# the agent never uttered, and two of the five baseline calls lost the same way.
#
# So every call runs the same three steps, in order, and the rescore is not
# optional — a raw run's speech metrics are not trustworthy:
#   1. place the call
#   2. rewrite agent turns from Samvaad's own transcription
#   3. re-score from the corrected transcript (no new session, no credits)
set -uo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
EVA=research/upstream/eva/.venv/bin/python
REC="${1:?usage: run_bot_call.sh RECORD_ID [account_id]}"
ACCT="${2:-EC-DEMO-$REC}"

echo "=== 1/3 placing $REC ==="
$PY scripts/pilot_state.py reset 4416 "$REC" "$ACCT" >/dev/null
before=$(ls -1d artifacts/eva_live/*/ 2>/dev/null | wc -l)
perl -e 'alarm shift; exec @ARGV' 420 "$EVA" scripts/run_eva_samvaad_live.py \
  --confirm-live --time-limit 120 --record-id "$REC" 2>&1 \
  | grep -E "Run ID:|Successful:|ERROR" | tail -3

RUN=$(ls -1td artifacts/eva_live/*/ | head -1 | xargs basename)
after=$(ls -1d artifacts/eva_live/*/ 2>/dev/null | wc -l)
if [ "$after" -le "$before" ]; then echo "  no new run directory — aborting"; exit 1; fi
echo "  run: $RUN"

echo "=== 2/3 repairing agent transcript from Samvaad ==="
$PY scripts/repair_agent_transcript.py --apply "$RUN" 2>&1 | grep -v "^$"

echo "=== 3/3 re-scoring on the corrected transcript ==="
perl -e 'alarm shift; exec @ARGV' 600 "$EVA" scripts/rescore_eva_samvaad_run.py "$RUN" 2>&1 \
  | grep -E "Successful:|ERROR" | tail -2

$PY - "$RUN" "$REC" <<'EOF'
import json, sys, glob
run, rec = sys.argv[1], sys.argv[2]
hits = glob.glob(f"artifacts/eva_live/{run}/records/{rec}*/metrics.json")
if not hits:
    print("  no metrics written — inspect the run directory"); raise SystemExit(1)
m = json.load(open(hits[0]))
a = m["aggregate_metrics"]
print(f"\n  EVA-A {a['EVA-A_mean']:.3f} | EVA-X {a['EVA-X_mean']:.3f}")
print("  " + json.dumps({k: v.get("normalized_score") for k, v in m["metrics"].items()}))
EOF
echo "=== done: $RUN ==="
