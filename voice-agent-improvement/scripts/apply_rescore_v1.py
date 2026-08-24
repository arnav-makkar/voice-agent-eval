"""Apply rubric.v1 judge scores to the dashboard evidence indexes.

Reads artifacts/campaign2/rescore/judge_scores.json plus the bot run-record
ledgers, enriches the four index.json files in place, and prints the aggregate
numbers the site's chips must show. Publishes scores exactly as returned.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from judge_rescore_v1 import DASH, RESCORE, bot_conversations, load_scenarios  # noqa: E402

NORM = {1: 0.0, 2: 0.25, 3: 0.5, 4: 0.75, 5: 1.0}


def rating_of(res: dict, metric: str):
    r = (res.get(metric) or {})
    if not r.get("ok"):
        return None, None
    p = r["parsed"]
    return int(p["rating"]), p.get("explanation", "")


def break_of(res: dict):
    r = res.get("breaking_turn") or {}
    if not r.get("ok"):
        return None
    p = r["parsed"]
    return {"agent_turn": int(p["turn"]), "reason": p.get("reason", ""), "kind": "judged"}


def phone_breaking_dupe(entry: dict):
    """Deterministic breaking turn for duplicate-write phone calls: the agent
    turn carrying the second write of the duplicated tool."""
    counts = Counter(entry.get("tools") or [])
    dup = [t for t, n in counts.items() if n > 1]
    if not dup:
        return None
    seen: Counter = Counter()
    agent_turn = 0
    for turn in entry["transcript"]:
        if turn["speaker"] == "agent":
            agent_turn += 1
        for tool in (turn.get("tools") or []):
            seen[tool["name"]] += 1
            if tool["name"] in dup and seen[tool["name"]] == 2:
                return {"agent_turn": agent_turn,
                        "reason": f"second identical {tool['name']} write",
                        "kind": "deterministic"}
    return None


def main() -> int:
    scores = json.loads((RESCORE / "judge_scores.json").read_text())["conversations"]
    bots = {c["key"]: c for c in bot_conversations(load_scenarios())}

    agg = {}
    for tier in ("phone", "bot"):
        for ver in ("v3", "v4"):
            path = DASH / f"{tier}-{ver}" / "index.json"
            idx = json.loads(path.read_text())
            for e in idx:
                key = f"{tier}-{ver}:{e['id']}"
                res = scores[key]["results"]
                notes = {}
                for m, field in (("faithfulness", "faithfulness"),
                                 ("conciseness", "conciseness"),
                                 ("conversation_progression", "progression")):
                    rating, note = rating_of(res, m)
                    if rating is None:
                        raise SystemExit(f"missing judge result: {key} {m}")
                    e[field] = NORM[rating]
                    e[f"{field}_rating"] = rating
                    notes[field] = note
                e["judge_notes"] = notes

                if tier == "bot":
                    b = bots[key]
                    e["tools"] = b["tools_flat"]
                    e["writes"] = b["ledger"]
                    e["missing"] = b["missing"]
                    e["disposition"] = b["disposition"]
                    dupes = {t: n for t, n in Counter(b["tools_flat"]).items() if n > 1}
                    e["duplicate_writes"] = dupes or None
                    e["exactly_once"] = not dupes
                    task = e["task_completion"]
                    e["eva_a"] = round((task + e["faithfulness"] + e["agent_speech_fidelity"]) / 3, 3)
                    e["passed"] = task == 1.0
                else:
                    dupes = {t: n for t, n in Counter(e.get("tools") or []).items() if n > 1}
                    e["duplicate_writes"] = dupes or None
                    e["exactly_once"] = not dupes
                    task = 1.0 if e["passed"] else 0.0
                    e["task_completion"] = task
                    e["eva_a"] = round((task + e["faithfulness"]) / 2, 3)
                e["eva_x"] = round((e["conciseness"] + e["progression"]) / 2, 3)

                bt = break_of(res)
                if bt is None and tier == "phone" and e["passed"]:
                    bt = phone_breaking_dupe(e)
                e["breaking_turn"] = bt

            path.write_text(json.dumps(idx, ensure_ascii=False, indent=1))
            agg[f"{tier}-{ver}"] = {
                "n": len(idx),
                "eva_a_mean": round(sum(x["eva_a"] for x in idx) / len(idx), 3),
                "eva_x_mean": round(sum(x["eva_x"] for x in idx) / len(idx), 3),
                "exactly_once": sum(1 for x in idx if x["exactly_once"]),
                "task_pass": sum(1 for x in idx if x.get("passed")),
                "ratings": {
                    m: sorted(x[f"{m}_rating"] for x in idx)
                    for m in ("faithfulness", "conciseness", "progression")
                },
            }

    print(json.dumps(agg, indent=1))
    (RESCORE / "aggregates.json").write_text(json.dumps(agg, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
