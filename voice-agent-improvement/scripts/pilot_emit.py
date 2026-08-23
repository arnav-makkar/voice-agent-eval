"""Emit one baseline scenario as a browser payload, and reset its ledger."""
import json, subprocess, sys
from pathlib import Path
SET = Path('/private/tmp/claude-501/-Users-Arnav-Claude-Projects-Sarvam/60097001-bfec-4eca-848b-e27953f27029/scratchpad/base10.json')
i = int(sys.argv[1])
s = json.loads(SET.read_text(encoding='utf-8'))[i]
subprocess.run(['.venv/bin/python','scripts/pilot_state.py','reset',s['outstanding']],capture_output=True)
print(f"# [{i}] {s['id']} {s['family']} {s['lang']} outstanding={s['outstanding']} (ledger reset)")
print('window.__S = '+json.dumps({'id':s['id'],'vals':s['vals'],'steps':s['steps']},ensure_ascii=False)+';')
