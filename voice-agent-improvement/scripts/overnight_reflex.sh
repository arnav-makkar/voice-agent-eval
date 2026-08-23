#!/bin/bash
# The overnight Reflex run: two fully autonomous generations from the committed
# baseline. Every phase writes its outputs before the next begins, and every
# phase is skipped if its output already exists, so a crash resumes with:
#   bash scripts/overnight_reflex.sh
# No human-authored candidate text anywhere: the seed is the committed v3
# instructions, the exemplars are machine-mined from measured calls, and every
# later candidate is model-proposed.
set -uo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
IMP=artifacts/campaign2/improvement
BULK=artifacts/campaign2/chat_bulk
LOG="$IMP/overnight.log"
mkdir -p "$IMP"
say() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }

# ── Phase 0: preconditions ───────────────────────────────────────────────────
say "P0 token check"
$PY - <<'EOF' || exit 1
import base64, json, time
tok = open('.env.local').read().split('=',1)[1].strip()
p = tok.split('.')[1]; p += '=' * (-len(p) % 4)
exp = json.loads(base64.urlsafe_b64decode(p))['exp']
hours = (exp - time.time()) / 3600
print(f"  token valid {hours:.1f}h")
assert hours > 7, "dashboard JWT expires too soon for an overnight run - recapture it first"
EOF

say "P0 tunnel + tool service"
curl -s -o /dev/null -w "  tunnel HTTP %{http_code}\n" --max-time 15 \
  https://despite-gtk-checked-knit.trycloudflare.com/health | tee -a "$LOG"
curl -s -o /dev/null --max-time 5 http://127.0.0.1:8788/health || { say "tool service down"; exit 1; }

# fresh blind sets + exemplars exist already (built and hashed before approval);
# regenerate only if missing
[ -f artifacts/framework/emi/benchmark_v1/blind_g2.jsonl ] || $PY scripts/build_fresh_blind.py
[ -f "$IMP/exemplars_seed.md" ] || $PY scripts/mine_exemplars.py
[ -f "$IMP/seed_v3_plain.md" ] || { say "missing v3 seed"; exit 1; }

# ── Phase 1: noise probe (H1) — the same seed, twice ─────────────────────────
if [ ! -f "$IMP/noise_probe.json" ]; then
  say "P1 noise probe: applying v3 seed to draft, 2x stratified probe"
  $PY - <<'EOF'
import sys; sys.path.insert(0, '.')
from framework.evaluation.adapters import indus_authoring as A
A.write_instructions(open('artifacts/campaign2/improvement/seed_v3_plain.md').read())
print("  v3 seed applied to draft")
EOF
  $PY scripts/noise_probe.py 2>&1 | tail -20 | tee -a "$LOG"
else
  say "P1 noise probe: exists, skipping"
fi

# ── Phase 2: Generation 1 — explore ──────────────────────────────────────────
if [ ! -f "$IMP/gen1_explore/best_candidate.json" ]; then
  say "P2 gen1 explore: GEPA budget 380, reflector gemini-3.1-pro-preview"
  $PY scripts/gepa_optimize.py --budget 380 \
    --seed-instructions "$IMP/seed_v3_plain.md" \
    --seed-exemplars "$IMP/exemplars_seed.md" \
    --run-dir "$IMP/gen1_explore" 2>&1 | tail -5 | tee -a "$LOG"
fi

# ── Phase 3: champion's development verdict → regressions + stuck ────────────
if [ ! -f "$BULK/g1x_development.jsonl" ]; then
  say "P3 gen1-explore champion on full development split"
  $PY - <<'EOF'
import sys, json; sys.path.insert(0, '.')
from scripts.gepa_optimize import apply_candidate
apply_candidate(json.load(open('artifacts/campaign2/improvement/gen1_explore/best_candidate.json')))
print("  explore champion applied")
EOF
  $PY scripts/run_chat_suite.py --split development --app-version 4 \
    --out "$BULK/g1x_development.jsonl" 2>&1 | tail -2 | tee -a "$LOG"
fi
$PY scripts/gen_regressions.py --parent v3 --champion g1x \
  --out-dir "$IMP/gen1_triage" | tee -a "$LOG"

# ── Phase 4: Generation 1 — consolidate (the systemic repair pass) ──────────
if [ ! -f "$IMP/gen1_consolidate/best_candidate.json" ]; then
  if [ "$(jq length "$IMP/gen1_triage/regressions.json")" -gt 0 ]; then
    say "P4 gen1 consolidate: budget 100 on regressions + protected fixes"
    $PY scripts/gepa_optimize.py --budget 100 \
      --run-dir "$IMP/gen1_consolidate" \
      --trainset-file "$IMP/gen1_triage/consolidation_trainset.json" \
      --consolidate-from "$IMP/gen1_explore/best_candidate.json" 2>&1 | tail -5 | tee -a "$LOG"
  else
    say "P4 no regressions — consolidation skipped"
    cp "$IMP/gen1_explore/best_candidate.json" "$IMP/gen1_consolidate_best_skipped.json" 2>/dev/null || true
  fi
fi

# pick gen1 final = higher valset score of the two champions
$PY - <<'EOF' | tee -a "$LOG"
import json, shutil
from pathlib import Path
imp = Path('artifacts/campaign2/improvement')
explore = json.loads((imp / 'gen1_explore/result_summary.json').read_text())
best_dir = imp / 'gen1_explore'
cons = imp / 'gen1_consolidate/result_summary.json'
if cons.exists():
    c = json.loads(cons.read_text())
    if (c.get('best_score') or 0) >= (explore.get('best_score') or 0):
        best_dir = imp / 'gen1_consolidate'
shutil.copy(best_dir / 'best_candidate.json', imp / 'gen1_final.json')
print(f"  gen1 final = {best_dir.name}")
EOF

# ── Phase 5: Generation 1 verdict — all 180, then gate ───────────────────────
say "P5 gen1 verdict on 180"
$PY - <<'EOF'
import sys, json; sys.path.insert(0, '.')
from scripts.gepa_optimize import apply_candidate
apply_candidate(json.load(open('artifacts/campaign2/improvement/gen1_final.json')))
print("  gen1 final applied")
EOF
for s in development validation regression synthetic; do
  [ -f "$BULK/g1_${s}.jsonl" ] || $PY scripts/run_chat_suite.py --split $s --app-version 4 \
    --out "$BULK/g1_${s}.jsonl" 2>&1 | tail -1 | tee -a "$LOG"
done

# ── Phase 6: Generation 2 — explore + consolidate from gen1, stuck excluded ──
$PY scripts/gen_regressions.py --parent v3 --champion g1 --out-dir "$IMP/gen2_triage" | tee -a "$LOG"
if [ ! -f "$IMP/gen2_explore/best_candidate.json" ]; then
  say "P6 gen2 explore: budget 300, stuck bucket excluded from search"
  $PY - <<'EOF'
import json
from pathlib import Path
imp = Path('artifacts/campaign2/improvement')
seed = json.loads((imp / 'gen1_final.json').read_text())
Path(imp / 'gen2_seed_instructions.md').write_text(seed.get('instructions', ''))
Path(imp / 'gen2_seed_exemplars.md').write_text(seed.get('exemplars', '') or ' ')
EOF
  $PY scripts/gepa_optimize.py --budget 300 \
    --seed-instructions "$IMP/gen2_seed_instructions.md" \
    --seed-exemplars "$IMP/gen2_seed_exemplars.md" \
    --run-dir "$IMP/gen2_explore" \
    --exclude-file "$IMP/gen2_triage/stuck.json" 2>&1 | tail -5 | tee -a "$LOG"
fi

if [ ! -f "$BULK/g2x_development.jsonl" ]; then
  say "P6b gen2-explore champion on development"
  $PY - <<'EOF'
import sys, json; sys.path.insert(0, '.')
from scripts.gepa_optimize import apply_candidate
apply_candidate(json.load(open('artifacts/campaign2/improvement/gen2_explore/best_candidate.json')))
EOF
  $PY scripts/run_chat_suite.py --split development --app-version 4 \
    --out "$BULK/g2x_development.jsonl" 2>&1 | tail -2 | tee -a "$LOG"
fi
$PY scripts/gen_regressions.py --parent g1 --champion g2x --out-dir "$IMP/gen2b_triage" | tee -a "$LOG"
if [ ! -f "$IMP/gen2_consolidate/best_candidate.json" ] && \
   [ "$(jq length "$IMP/gen2b_triage/regressions.json")" -gt 0 ]; then
  say "P6c gen2 consolidate"
  $PY scripts/gepa_optimize.py --budget 100 \
    --run-dir "$IMP/gen2_consolidate" \
    --trainset-file "$IMP/gen2b_triage/consolidation_trainset.json" \
    --consolidate-from "$IMP/gen2_explore/best_candidate.json" 2>&1 | tail -5 | tee -a "$LOG"
fi
$PY - <<'EOF' | tee -a "$LOG"
import json, shutil
from pathlib import Path
imp = Path('artifacts/campaign2/improvement')
best_dir = imp / 'gen2_explore'
cons = imp / 'gen2_consolidate/result_summary.json'
if cons.exists():
    c = json.loads(cons.read_text())
    e = json.loads((imp / 'gen2_explore/result_summary.json').read_text())
    if (c.get('best_score') or 0) >= (e.get('best_score') or 0):
        best_dir = imp / 'gen2_consolidate'
shutil.copy(best_dir / 'best_candidate.json', imp / 'gen2_final.json')
print(f"  gen2 final = {best_dir.name}")
EOF

# ── Phase 7: Generation 2 verdict — 180 + fresh blind_g2 (first touch) ───────
say "P7 gen2 verdict on 180 + fresh blind"
$PY - <<'EOF'
import sys, json; sys.path.insert(0, '.')
from scripts.gepa_optimize import apply_candidate
apply_candidate(json.load(open('artifacts/campaign2/improvement/gen2_final.json')))
print("  gen2 final applied")
EOF
for s in development validation regression synthetic blind_g2; do
  [ -f "$BULK/g2_${s}.jsonl" ] || $PY scripts/run_chat_suite.py --split $s --app-version 4 \
    --out "$BULK/g2_${s}.jsonl" 2>&1 | tail -1 | tee -a "$LOG"
done
# baseline must also be measured on the fresh blind for a fair rung
[ -f "$BULK/v3b_blind_g2.jsonl" ] || {
  say "P7b baseline on fresh blind (for the g2 rung denominator)"
  $PY - <<'EOF'
import sys; sys.path.insert(0, '.')
from framework.evaluation.adapters import indus_authoring as A
A.write_instructions(open('artifacts/campaign2/improvement/seed_v3_plain.md').read())
EOF
  $PY scripts/run_chat_suite.py --split blind_g2 --app-version 4 \
    --out "$BULK/v3b_blind_g2.jsonl" 2>&1 | tail -1 | tee -a "$LOG"
  # restore gen2 champion to the draft afterwards
  $PY - <<'EOF'
import sys, json; sys.path.insert(0, '.')
from scripts.gepa_optimize import apply_candidate
apply_candidate(json.load(open('artifacts/campaign2/improvement/gen2_final.json')))
EOF
}

# ── Phase 8: ladder + stats ──────────────────────────────────────────────────
say "P8 ladder report"
$PY scripts/reflex_report.py --rungs v3:g1 g1:g2 v3:g2 2>&1 | tee -a "$LOG"
say "OVERNIGHT REFLEX COMPLETE — champion is on the draft, uncommitted"
