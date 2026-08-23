"""Render the standalone owner label-review app.

The payload is embedded directly in the HTML so the reviewer can open the file
from disk without a server.  The app never writes into the repository; it exports
a download that `ingest_owner_labels` converts into versioned owner truth.
"""

from __future__ import annotations

import json
from pathlib import Path

from framework.datasets.build_label_review import OUTPUT as PAYLOAD_PATH
from framework.datasets.build_label_review import build

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "artifacts" / "framework" / "emi" / "label_review" / "review-20-calls.html"

FAILURE_CATEGORIES = [
    "none",
    "redundant_confirmation",
    "conditional_check_not_converted",
    "trust_resolution_missing_direct_close",
    "repeated_pressure_after_channel_refusal",
    "channel_unavailable_loop",
    "caller_disengagement_after_interruption",
    "dispute_misclassified_wrong_number",
    "invalid_output_disposition",
    "unsupported_future_completion_claim",
    "late_charge_misstatement",
    "other",
]

FAILURE_OWNERS = [
    "none",
    "agent_prompt",
    "output_extractor",
    "tool",
    "workflow",
    "knowledge_or_policy",
    "model_or_runtime",
    "voice_or_channel",
    "simulator_or_caller",
    "mixed",
]

SEVERITIES = ["none", "P0", "P1", "P2", "P3"]

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Owner Label Review</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{--bg:#0B0E14;--panel:#121724;--panel2:#171E30;--inset:#0D1220;--line:rgba(148,159,184,.16);--line2:rgba(148,159,184,.32);--ink:#E9EDF6;--mut:#98A1B6;--dim:#6C7690;--acc:#7C9EFF;--good:#46D39A;--warn:#F0BA5E;--bad:#F2788F;--disp:"Archivo",system-ui,sans-serif;--body:"IBM Plex Sans",system-ui,sans-serif;--mono:"IBM Plex Mono",ui-monospace,monospace}
*{box-sizing:border-box;margin:0}
body{background:var(--bg);color:var(--ink);font:14px/1.6 var(--body);height:100vh;overflow:hidden}
button{font:inherit;cursor:pointer}
button:focus-visible,select:focus-visible,textarea:focus-visible,input:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
header{display:flex;align-items:center;gap:16px;padding:12px 20px;border-bottom:1px solid var(--line);background:var(--panel)}
header h1{font:700 15px var(--disp)}
header .sp{margin-left:auto;display:flex;align-items:center;gap:12px}
.bar{width:220px;height:6px;background:var(--inset);border-radius:99px;overflow:hidden}
.bar i{display:block;height:100%;background:var(--good);transition:width .2s}
.count{font:500 12px var(--mono);color:var(--mut);font-variant-numeric:tabular-nums}
.btn{background:var(--acc);color:#08101f;border:0;border-radius:8px;padding:8px 14px;font-weight:600;font-size:13px}
.btn.ghost{background:transparent;color:var(--mut);border:1px solid var(--line2)}
main{display:grid;grid-template-columns:230px 1fr 380px;height:calc(100vh - 57px)}
aside.list{border-right:1px solid var(--line);overflow-y:auto;background:var(--panel)}
aside.list button{display:flex;align-items:center;gap:9px;width:100%;text-align:left;background:none;border:0;border-bottom:1px solid var(--line);color:var(--mut);padding:10px 14px;font:500 12px var(--mono)}
aside.list button:hover{background:var(--panel2);color:var(--ink)}
aside.list button.on{background:var(--panel2);color:var(--ink);box-shadow:inset 3px 0 0 var(--acc)}
.dot{width:8px;height:8px;border-radius:50%;background:var(--dim);flex:none}
.dot.done{background:var(--good)}
.dot.edited{background:var(--warn)}
section.mid{overflow-y:auto;padding:22px 26px}
.ctx{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:16px}
.tag{font:500 11px var(--mono);padding:3px 9px;border-radius:99px;border:1px solid var(--line2);color:var(--mut)}
.tag b{color:var(--ink);font-weight:600}
h2.run{font:700 20px var(--disp);margin-bottom:4px}
p.sub{color:var(--mut);font-size:13px;margin-bottom:18px}
.turn{display:grid;grid-template-columns:44px 1fr;gap:12px;padding:9px 0;border-top:1px solid var(--line)}
.turn:first-of-type{border-top:0}
.tn{font:600 11px var(--mono);color:var(--dim);padding-top:3px}
.who{font:600 11px var(--mono);letter-spacing:.05em;text-transform:uppercase;margin-bottom:3px}
.agent .who{color:var(--acc)}
.caller .who{color:var(--good)}
.turn p{font-size:14px}
.turn.mark{background:rgba(240,186,94,.07);box-shadow:inset 3px 0 0 var(--warn);border-radius:0 6px 6px 0;padding-left:9px;margin-left:-9px}
.turn.mark .tn{color:var(--warn)}
aside.form{border-left:1px solid var(--line);overflow-y:auto;padding:20px;background:var(--panel)}
.lab{font:600 10.5px var(--mono);letter-spacing:.09em;text-transform:uppercase;color:var(--dim);margin:16px 0 7px;display:block}
.lab:first-child{margin-top:0}
.prov{background:var(--inset);border:1px solid var(--line);border-radius:8px;padding:11px 13px;font-size:12.5px;color:var(--mut);margin-bottom:6px}
.prov b{color:var(--ink);font-weight:600}
select,textarea,input[type=number]{width:100%;background:var(--inset);border:1px solid var(--line2);color:var(--ink);border-radius:8px;padding:8px 10px;font:500 13px var(--body)}
textarea{font-family:var(--body);min-height:64px;resize:vertical}
.seg{display:flex;gap:6px}
.seg button{flex:1;background:var(--inset);border:1px solid var(--line2);color:var(--mut);border-radius:8px;padding:7px;font-size:12.5px;font-weight:600}
.seg button.on-t{background:rgba(70,211,154,.16);border-color:var(--good);color:var(--good)}
.seg button.on-f{background:rgba(242,120,143,.16);border-color:var(--bad);color:var(--bad)}
.diff{font:500 11px var(--mono);color:var(--warn);margin-top:5px}
.acts{display:flex;gap:8px;margin-top:20px;position:sticky;bottom:0;background:var(--panel);padding-top:12px}
.acts .btn{flex:1}
.hint{color:var(--dim);font-size:11.5px;margin-top:12px;line-height:1.5}
kbd{font:500 10.5px var(--mono);background:var(--inset);border:1px solid var(--line2);border-radius:4px;padding:1px 5px;color:var(--mut)}
</style>
</head>
<body>
<header>
  <h1>Owner label review · 20 V12 discovery calls</h1>
  <div class="sp">
    <span class="count" id="cnt">0 / 20 reviewed</span>
    <div class="bar"><i id="bar" style="width:0%"></i></div>
    <button class="btn ghost" id="save">Save progress</button>
    <button class="btn" id="export">Export owner labels</button>
  </div>
</header>
<main>
  <aside class="list" id="list"></aside>
  <section class="mid" id="mid"></section>
  <aside class="form" id="form"></aside>
</main>
<script id="payload" type="application/json">__PAYLOAD__</script>
<script>
const DATA = JSON.parse(document.getElementById('payload').textContent);
const CATS = __CATS__, OWNERS = __OWNERS__, SEVS = __SEVS__;
const KEY = 'framework-owner-label-review-v1';
let state = JSON.parse(localStorage.getItem(KEY) || '{}');
let idx = 0;

const rec = () => DATA.records[idx];
const cur = (id) => state[id] || (state[id] = {reviewed:false, labels:{}, comment:''});
const val = (r,f) => { const s = cur(r.run_id); return f in s.labels ? s.labels[f] : r.provisional[f]; };
const changed = (r,f) => { const s = cur(r.run_id); return f in s.labels && String(s.labels[f]) !== String(r.provisional[f]); };
const save = () => localStorage.setItem(KEY, JSON.stringify(state));

function progress(){
  const n = DATA.records.filter(r => state[r.run_id]?.reviewed).length;
  document.getElementById('cnt').textContent = `${n} / ${DATA.records.length} reviewed`;
  document.getElementById('bar').style.width = `${(n/DATA.records.length)*100}%`;
}

function renderList(){
  document.getElementById('list').innerHTML = DATA.records.map((r,i)=>{
    const s = state[r.run_id];
    const edited = s && Object.keys(s.labels||{}).some(f=>String(s.labels[f])!==String(r.provisional[f]));
    const cls = s?.reviewed ? (edited?'edited':'done') : '';
    return `<button class="${i===idx?'on':''}" data-i="${i}"><span class="dot ${cls}"></span>${r.run_id}</button>`;
  }).join('');
  [...document.querySelectorAll('#list button')].forEach(b=>b.onclick=()=>{idx=+b.dataset.i;render();});
}

function renderMid(){
  const r = rec(), brk = val(r,'first_breaking_turn');
  document.getElementById('mid').innerHTML = `
    <h2 class="run">${r.run_id}</h2>
    <p class="sub">${r.scenario_note || 'Controlled discovery call'} · ${r.attempt.language_name || ''} · ${(r.attempt.duration_seconds||0).toFixed(0)}s · ended by ${(r.attempt.ended_by||'').replace(/_/g,' ').toLowerCase()}</p>
    <div class="ctx">
      <span class="tag">role <b>${r.corpus_role}</b></span>
      <span class="tag">eligible <b>${r.primary_eligible}</b></span>
      <span class="tag">expected <b>${r.expected_disposition||'—'}</b></span>
      <span class="tag">observed <b>${r.observed_disposition||'—'}</b></span>
      <span class="tag">agent latency <b>${r.attempt.average_agent_response_time_in_seconds ?? '—'}s</b></span>
    </div>
    ${r.transcript.map(t=>`
      <div class="turn ${t.role==='assistant'?'agent':'caller'} ${t.turn_id===brk?'mark':''}">
        <span class="tn">T${t.turn_id}</span>
        <div><p class="who">${t.role==='assistant'?'Shubh · agent':'Arnav · caller'}</p><p>${t.content}</p></div>
      </div>`).join('')}
    <p class="hint">The highlighted turn is where the provisional label says the call first broke. If you disagree, change the turn number on the right.</p>`;
}

function bool(f,label){
  const r=rec(), v=val(r,f);
  return `<span class="lab">${label}</span>
    <div class="seg">
      <button data-f="${f}" data-v="true" class="${v===true?'on-t':''}">True</button>
      <button data-f="${f}" data-v="false" class="${v===false?'on-f':''}">False</button>
    </div>${changed(r,f)?`<p class="diff">changed from ${r.provisional[f]}</p>`:''}`;
}

function renderForm(){
  const r=rec(), s=cur(r.run_id);
  document.getElementById('form').innerHTML = `
    <span class="lab">Provisional note (Codex-assisted)</span>
    <div class="prov">${r.provisional_note || '—'}</div>
    ${bool('primary_success','Primary success — explicit pay-now')}
    ${bool('task_success','Task success — correct outcome captured')}
    <span class="lab">First breaking turn</span>
    <input type="number" id="brk" min="0" value="${val(r,'first_breaking_turn') ?? ''}">
    ${changed(r,'first_breaking_turn')?`<p class="diff">changed from ${r.provisional.first_breaking_turn}</p>`:''}
    <span class="lab">Failure category</span>
    <select id="cat">${CATS.map(c=>`<option ${String(val(r,'failure_category')??'none')===c?'selected':''}>${c}</option>`).join('')}</select>
    ${changed(r,'failure_category')?`<p class="diff">changed from ${r.provisional.failure_category}</p>`:''}
    <span class="lab">Failure owner</span>
    <select id="own">${OWNERS.map(c=>`<option ${String(val(r,'failure_owner')??'none')===c?'selected':''}>${c}</option>`).join('')}</select>
    ${changed(r,'failure_owner')?`<p class="diff">changed from ${r.provisional.failure_owner}</p>`:''}
    <span class="lab">Severity</span>
    <select id="sev">${SEVS.map(c=>`<option ${String(val(r,'severity')??'none')===c?'selected':''}>${c}</option>`).join('')}</select>
    ${bool('integrity_violation','Integrity violation')}
    ${bool('hard_safety_violation','Hard safety violation')}
    <span class="lab">Your note</span>
    <textarea id="cmt" placeholder="Why you agreed or corrected…">${s.comment||''}</textarea>
    <div class="acts">
      <button class="btn ghost" id="prev">← Prev</button>
      <button class="btn" id="ok">${s.reviewed?'Reviewed ✓':'Confirm & next'}</button>
    </div>
    <p class="hint">Everything defaults to the provisional label, so confirming an agreement is one click. <kbd>J</kbd> next · <kbd>K</kbd> prev · <kbd>Enter</kbd> confirm. Progress saves in this browser automatically.</p>`;

  [...document.querySelectorAll('.seg button')].forEach(b=>b.onclick=()=>{
    cur(rec().run_id).labels[b.dataset.f] = b.dataset.v==='true'; save(); render();
  });
  const set=(el,f,cast)=>el.onchange=()=>{cur(rec().run_id).labels[f]=cast(el.value);save();render();};
  set(document.getElementById('brk'),'first_breaking_turn',v=>v===''?null:+v);
  set(document.getElementById('cat'),'failure_category',v=>v);
  set(document.getElementById('own'),'failure_owner',v=>v);
  set(document.getElementById('sev'),'severity',v=>v);
  document.getElementById('cmt').oninput=e=>{cur(rec().run_id).comment=e.target.value;save();};
  document.getElementById('ok').onclick=confirmNext;
  document.getElementById('prev').onclick=()=>{idx=Math.max(0,idx-1);render();};
}

function confirmNext(){
  cur(rec().run_id).reviewed = true; save();
  if (idx < DATA.records.length-1) idx++;
  render();
}
function render(){ renderList(); renderMid(); renderForm(); progress(); }

document.onkeydown = e => {
  if (['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName)) return;
  if (e.key==='j'){ idx=Math.min(DATA.records.length-1,idx+1); render(); }
  if (e.key==='k'){ idx=Math.max(0,idx-1); render(); }
  if (e.key==='Enter'){ confirmNext(); }
};
document.getElementById('save').onclick=()=>{save();alert('Progress saved in this browser.');};
document.getElementById('export').onclick=()=>{
  const out = DATA.records.map(r=>{
    const s = cur(r.run_id);
    const labels = {};
    for (const f of DATA.review_fields) labels[f] = val(r,f);
    return {trace_id:r.run_id, review_status: s.reviewed?'owner_reviewed':'not_reviewed',
            labels, owner_comment:s.comment||'', provisional_content_hash:r.content_hash,
            changed_fields: Object.keys(s.labels||{}).filter(f=>String(s.labels[f])!==String(r.provisional[f]))};
  });
  const n = out.filter(o=>o.review_status==='owner_reviewed').length;
  if (n < DATA.records.length && !confirm(`Only ${n} of ${DATA.records.length} are reviewed. Export anyway?`)) return;
  const blob = new Blob([JSON.stringify({schema_version:'owner-label-export.v1',reviewed_count:n,records:out},null,2)],{type:'application/json'});
  const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='owner_labels_export.json'; a.click();
};
render();
</script>
</body>
</html>
"""


def render(output: Path = OUTPUT) -> Path:
    payload = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8")) if PAYLOAD_PATH.exists() else build()
    html = (
        TEMPLATE.replace("__PAYLOAD__", json.dumps(payload))
        .replace("__CATS__", json.dumps(FAILURE_CATEGORIES))
        .replace("__OWNERS__", json.dumps(FAILURE_OWNERS))
        .replace("__SEVS__", json.dumps(SEVERITIES))
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return output


if __name__ == "__main__":
    print(f"Review app written to {render()}")
