"""Score one baseline scenario against the ledger and append to a run file."""
import json, subprocess, sys
from pathlib import Path
sys.path.insert(0,'scripts')
from pilot_record import score
SET = Path('/private/tmp/claude-501/-Users-Arnav-Claude-Projects-Sarvam/60097001-bfec-4eca-848b-e27953f27029/scratchpad/base10.json')
i=int(sys.argv[1]); run=sys.argv[2]
s=json.loads(SET.read_text(encoding='utf-8'))[i]
tr=Path(sys.argv[3]).read_text(encoding="utf-8") if len(sys.argv)>3 else ""
eff=json.loads(subprocess.run(['.venv/bin/python','scripts/pilot_state.py','read'],capture_output=True,text=True).stdout)
res=score(s,eff)
out=Path('artifacts/campaign2/chat_pilot')/f'{run}.jsonl'
with out.open('a',encoding='utf-8') as fh:
    fh.write(json.dumps({"scenario":s,"effects":eff,"result":res,"transcript":tr},ensure_ascii=False)+"\n")
mark='PASS' if res['passed'] else 'fail'
print(f"[{i}] {s['id']} {s['family']:<21} {mark}  disp={res['observed_disposition']} called={res['tools_called']} missing={res['tools_missing']}")
