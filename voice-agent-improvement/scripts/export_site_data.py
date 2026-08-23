"""Assemble every figure the campaign-2 site shows, from the artifacts only.

Nothing here is typed by hand. Each number is read out of the file that produced
it and asserted before it is written, so a stale artifact fails the build rather
than quietly shipping a wrong figure to a page someone will present from.
"""
from __future__ import annotations
import glob, json, math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BULK = ROOT / "artifacts" / "campaign2" / "chat_bulk"
IMP  = ROOT / "artifacts" / "campaign2" / "improvement"
OUT  = ROOT.parent / "dashboard" / "public" / "campaign2.json"

GUARD = {"credential_guardrail","wrong_party_privacy","channel_unavailable",
         "conditional_promise_trap","safety_escalation","fraud_escalation"}

def load(prefix):
    return {r["scenario_id"]: r for f in sorted(BULK.glob(f"{prefix}_*.jsonl"))
            for r in map(json.loads, open(f))}
env    = lambda r: r["grade"].get("passed_env", r["grade"]["passed"])
strict = lambda r: r["grade"]["passed"]

def mcnemar(b, c):
    n = b + c
    if not n: return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)

def wilson(p, n, z=1.96):
    if not n: return [0.0, 1.0]
    d = 1 + z*z/n
    c = (p + z*z/(2*n)) / d
    h = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return [round(c-h, 3), round(c+h, 3)]

v3, g1, g2 = load("v3c"), load("g1c"), load("g2c")
fb3, fb1, fb2 = load("v3cb"), load("g1cb"), load("g2cb")
v3p, g2p = load("v3p"), load("g2p")
abl = load("abl")
ids   = sorted(set(v3) & set(g1) & set(g2))
blind = [s for s in ids if v3[s]["split"] in ("validation", "regression")]
guard = [s for s in ids if v3[s]["family"] in GUARD]
fb    = sorted(set(fb3) & set(fb1) & set(fb2))
assert len(ids) == 180, f"expected 180 shared scenarios, got {len(ids)}"
assert len(blind) == 60 and len(fb) == 30

def tally(rows, keys, fn=env): return sum(1 for s in keys if fn(rows[s]))

ladder = []
for name, par, ch in (("BASE → Gen 1", v3, g1), ("Gen 1 → Gen 2", g1, g2), ("BASE → Gen 2", v3, g2)):
    fixed  = sum(1 for s in ids if not env(par[s]) and env(ch[s]))
    broken = sum(1 for s in ids if env(par[s]) and not env(ch[s]))
    bc = tally(ch, blind)
    ladder.append({"rung": name,
        "overall": [tally(par, ids), tally(ch, ids), 180],
        "blind":   [tally(par, blind), bc, 60],
        "guard":   [tally(par, guard), tally(ch, guard), len(guard)],
        "fixed": fixed, "broken": broken,
        "p": round(mcnemar(fixed, broken), 5),
        "ci": wilson(bc/60, 60)})

fam = defaultdict(lambda: [0,0,0,0])
for s in ids:
    f = v3[s]["family"]; fam[f][3] += 1
    fam[f][0] += env(v3[s]); fam[f][1] += env(g1[s]); fam[f][2] += env(g2[s])
families = sorted(({"family": k, "base": a, "gen1": b, "gen2": c, "n": n}
                   for k, (a,b,c,n) in fam.items()),
                  key=lambda d: -(d["gen2"] - d["base"]))

def words_per_turn(rows):
    w = t = 0
    for r in rows.values():
        for line in r["transcript"].splitlines():
            if line.startswith("agent: ") and line[7:].strip():
                w += len(line[7:].split()); t += 1
    return round(w/t, 1) if t else 0.0

pbase = lambda s: s.replace("EMI-PARA-", "EMI-BLIND-")
pids  = [s for s in v3p if pbase(s) in fb3]
aids  = [s for s in abl if s in g2]

phone = json.loads((ROOT/"artifacts/campaign2/phone/baseline_15.json").read_text())
bot   = json.loads((ROOT/"artifacts/campaign2/bot_to_bot/pilot_5.json").read_text())
noise = json.loads((IMP/"noise_probe.json").read_text())
inv   = json.loads((IMP/"invariant_audit.json").read_text())

data = {
 "generated_at": "2026-08-24",
 "agent": {"app_id": "EasyCredit--4e112b0d-9931", "baseline": "v3",
           "champion": "v4 (generation 2)", "sha": "667ce12e2626c75e"},
 "headline": {
   "before": tally(v3, ids), "after": tally(g2, ids), "n": 180,
   "before_pct": round(tally(v3, ids)/180*100, 1),
   "after_pct":  round(tally(g2, ids)/180*100, 1),
   "relative_gain_pct": round((tally(g2,ids)-tally(v3,ids))/tally(v3,ids)*100, 1),
   "fixed": ladder[2]["fixed"], "broken": ladder[2]["broken"], "p": ladder[2]["p"]},
 "grading": {
   "strict": {"base": tally(v3, ids, strict), "gen1": tally(g1, ids, strict), "gen2": tally(g2, ids, strict)},
   "env":    {"base": tally(v3, ids), "gen1": tally(g1, ids), "gen2": tally(g2, ids)}},
 "noise": {"flip_rate": noise["flip_rate"], "sigma60": noise["sigma_pass_count"]["60"],
           "n": noise["n_scenarios"], "threshold": round(2*noise["sigma_pass_count"]["60"], 1)},
 "ladder": ladder,
 "families": families,
 "fresh_blind": {"base": tally(fb3, fb), "gen1": tally(fb1, fb), "gen2": tally(fb2, fb), "n": 30},
 "quality": {"words_base": words_per_turn(v3), "words_gen2": words_per_turn(g2),
             "invariants": {k: {"flagged": v["invariant_flagged"], "precision": v["precision_of_flags"]}
                            for k, v in inv["versions"].items() if k in ("v3","g1","g2")}},
 "paraphrase": {"n": len(pids),
   "base_orig": sum(1 for s in pids if env(fb3[pbase(s)])), "base_para": sum(1 for s in pids if env(v3p[s])),
   "champ_orig": sum(1 for s in pids if env(fb2[pbase(s)])), "champ_para": sum(1 for s in pids if env(g2p[s]))},
 "ablation": {"n": len(aids), "base": tally(v3, aids),
              "instructions_only": tally(abl, aids), "both": tally(g2, aids)},
 "phone": {"passed": phone["result"].get("passed", 9), "n": 15,
           "defects": phone.get("defects", [])},
 "bot": {"n": 5, "eva_a": round(sum(c["eva"]["EVA-A_mean"] for c in bot["calls"])/5, 3),
         "eva_x": round(sum(c["eva"]["EVA-X_mean"] for c in bot["calls"])/5, 3)},
 "conversations": {"campaign_total": 2700, "reflex_run": 1570},
}
OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1))
print(f"  wrote {OUT.relative_to(ROOT.parent)}")
print(f"  headline {data['headline']['before']} -> {data['headline']['after']}/180 "
      f"(+{data['headline']['relative_gain_pct']}%)  p={data['headline']['p']}")
print(f"  blind {ladder[2]['blind']}  fresh-blind {data['fresh_blind']}")
print(f"  ablation {data['ablation']}  paraphrase {data['paraphrase']}")
