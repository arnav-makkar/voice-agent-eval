"""Rescore phone and bot-to-bot conversations with the rubric.v1 judges.

Reads stored transcripts and ledgers only; never opens a new conversation.
Writes a provenance artifact with every prompt and raw response, then enriches
the dashboard evidence indexes in place. Scores are published as returned.

Usage:
  python3 scripts/judge_rescore_v1.py --smoke     # 2 conversations, print raw
  python3 scripts/judge_rescore_v1.py             # full run
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT.parent / "dashboard" / "public" / "evidence" / "audio"
RESCORE = ROOT / "artifacts" / "campaign2" / "rescore"
RUBRIC = (RESCORE / "RUBRIC.md").read_text()

JUDGE_MODEL = "gemini-3.1-pro-preview"
API = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={k}"

# ---------------------------------------------------------------- data loading


def load_env_key() -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip().strip("'\"")
    raise SystemExit("GEMINI_API_KEY not found in .env")


def load_scenarios() -> dict:
    out = {}
    for p in (
        ROOT / "artifacts/framework/emi/benchmark_v1/development.jsonl",
        ROOT / "artifacts/framework/emi/voice_stress_v1/scenarios.jsonl",
    ):
        for line in p.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                out[r["scenario_id"]] = r
    return out


def load_prompts() -> dict:
    return {
        "v3": (ROOT / "artifacts/campaign2/improvement/gen1_explore/seed_prompt.md").read_text(),
        "v4": (ROOT / "artifacts/campaign2/prompt.pre_end_interaction.md").read_text(),
    }


def _phone_service_journal() -> dict:
    """run_id -> ordered [{name, args}] from the tool service inbound log."""
    out: dict[str, list] = {}
    path = ROOT / "artifacts/tool_service/inbound_requests.jsonl"
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("method") != "POST" or r.get("status") != 200:
            continue
        if not str(r.get("path", "")).startswith("/v1/tools/"):
            continue
        body = r.get("body") or {}
        rid = body.get("run_id")
        if not rid:
            continue
        name = r["path"].rsplit("/", 1)[-1].replace("-", "_")
        out.setdefault(rid, []).append(
            {"at": r.get("at", ""), "name": name, "args": _clean_args(body)})
    for rid in out:
        out[rid] = [{"name": w["name"], "args": w["args"]}
                    for w in sorted(out[rid], key=lambda w: w["at"])]
    return out


def phone_conversations(scen: dict) -> list[dict]:
    sheet = {c["card"]: c for c in json.loads(
        (ROOT / "artifacts/campaign2/phone/call_sheet_v4.json").read_text())}
    service = _phone_service_journal()
    convs = []
    for ver in ("v3", "v4"):
        idx = json.loads((DASH / f"phone-{ver}" / "index.json").read_text())
        for c in idx:
            card = sheet[c["card"]]
            s = scen[card["scenario_id"]]
            convs.append({
                "key": f"phone-{ver}:{c['id']}",
                "tier": "phone", "ver": ver, "id": c["id"],
                "transcript": c["transcript"],
                "ledger": ([t for turn in c["transcript"] for t in (turn.get("tools") or [])]
                           or service.get(f"c2-phone-{c['card']:02d}-{ver}", [])
                           or [{"name": t, "args": None} for t in (c.get("tools") or [])]),
                "tools_flat": c.get("tools") or [],
                "scenario_ref": card["scenario_id"],
                "goal": s.get("user_goal", ""),
                "facts": fmt_facts(s),
                "accepted": s.get("accepted_dispositions", []),
                "required_full": s.get("required_actions", []),
                "required": card["required"],
                "passed": bool(c["passed"]),
                "language": c.get("language") or card.get("language", "hinglish"),
            })
    return convs


def _agent_texts(transcript: list[dict]) -> list[str]:
    return [t["text"].strip() for t in transcript if t.get("speaker") == "agent"]


def _match_run_record(scenario_id: str, app_version: int, agent_texts: list[str]) -> tuple[str, dict] | None:
    """Bind a dashboard bot entry to the eva_live record it was built from.

    Pure transcript matching: the run configs' app_version is not authoritative
    (the platform serves the draft), so the conversation text is the identity.
    """
    import glob
    best, best_score = None, 0.0
    for tpath in glob.glob(str(ROOT / "artifacts/eva_live/*/records/*/transcript.jsonl")):
        rec_agent = []
        for line in Path(tpath).read_text().splitlines():
            try:
                e = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            if e.get("type") == "assistant" and e.get("content"):
                rec_agent.append(str(e["content"]).strip())
        if not rec_agent:
            continue
        hits = sum(1 for a in agent_texts if any(a[:40] and a[:40] in b for b in rec_agent))
        score = hits / max(1, len(agent_texts))
        if score > best_score:
            best, best_score = str(Path(tpath).parent), score
    if best and best_score >= 0.5:
        return best, {"match": best_score}
    return None


def _clean_args(args: dict | None) -> dict:
    drop = {"run_id", "account_id", "event_id"}
    return {k: v for k, v in (args or {}).items() if k not in drop}


BOT_GOALS = {
    "pay-now": "Agree to pay now, once asked directly.",
    "callback": "Ask for a callback at a specific date and time window.",
    "refusal": "Refuse to pay outright and hold that refusal.",
    "dispute": "Dispute the debt: the caller says he never bought the TV and the loan is not his.",
    "distress": "Genuine distress: job loss and a hospitalised father. Needs a human, not a collections push.",
}

BOT_FACT_KEYS = ("outstandingAmount", "emiAmount", "lateChargeAmount", "dueDate", "daysPastDue",
                 "productName", "merchantName", "customerCareNumber", "fraudHelplineNumber")


def bot_conversations(scen: dict) -> list[dict]:
    convs = []
    for ver in ("v3", "v4"):
        idx = json.loads((DASH / f"bot-{ver}" / "index.json").read_text())
        for c in idx:
            agent_texts = _agent_texts(c["transcript"])
            m = _match_run_record(c["scenario_id"], int(ver[1]), agent_texts)
            if not m:
                raise SystemExit(f"unresolved bot conversation: {ver}:{c['id']}")
            rec = Path(m[0])
            state = json.loads((rec / "loopline_tool_state.json").read_text())
            sdb = json.loads((rec / "scenario_db.json").read_text())
            ev = sdb.get("evaluation") or {}
            if not ev.get("accepted_dispositions") and c["scenario_id"] in scen:
                fb = scen[c["scenario_id"]]
                ev = {"required_actions": fb.get("required_actions", []),
                      "accepted_dispositions": fb.get("accepted_dispositions", []),
                      "source_scenario_id": "benchmark fallback"}
            ledger = [{"name": e["tool_name"], "args": _clean_args(e.get("arguments"))}
                      for e in state.get("events", [])]
            tools_flat = [w["name"] for w in ledger]
            required = [a["name"] for a in ev.get("required_actions", [])]
            facts = {k: v for k, v in (sdb.get("agent_variables") or {}).items() if k in BOT_FACT_KEYS}
            facts.update(sdb.get("customer") or {})
            convs.append({
                "key": f"bot-{ver}:{c['id']}",
                "tier": "bot", "ver": ver, "id": c["id"],
                "transcript": c["transcript"],
                "ledger": ledger,
                "tools_flat": tools_flat,
                "run_record": str(rec),
                "match_quality": m[1]["match"],
                "disposition": (state.get("state") or {}).get("disposition"),
                "missing": [r for r in required if r not in tools_flat],
                "scenario_ref": f"{c['scenario_id']} ({ev.get('source_scenario_id', '?')})",
                "goal": BOT_GOALS.get(c["id"], ""),
                "facts": json.dumps(facts, ensure_ascii=False, indent=1),
                "accepted": ev.get("accepted_dispositions", []),
                "required_full": ev.get("required_actions", []),
                "required": required,
                "passed": c["task_completion"] == 1.0,
                "language": "hinglish",
            })
    return convs


# ---------------------------------------------------------------- prompt build


def fmt_transcript(t: list[dict]) -> str:
    lines, n = [], 0
    for turn in t:
        who = "agent" if turn["speaker"] == "agent" else "caller"
        if who == "agent":
            n += 1
            lines.append(f"T{n} agent: {turn['text']}")
        else:
            lines.append(f"   caller: {turn['text']}")
        for tool in (turn.get("tools") or []):
            lines.append(f"   [tool_call in this turn: {tool['name']}({json.dumps(tool.get('args'), ensure_ascii=False)})]")
    return "\n".join(lines)


def fmt_ledger(conv: dict) -> str:
    if not conv["tools_flat"]:
        return "(the log holds no writes for this conversation)"
    out = []
    for i, w in enumerate(conv["ledger"], 1):
        if isinstance(w, dict) and w.get("args") is not None:
            out.append(f"{i}. {w['name']}({json.dumps(w.get('args'), ensure_ascii=False)})")
        else:
            name = w["name"] if isinstance(w, dict) else w
            out.append(f"{i}. {name}")
    return "\n".join(out)


def fmt_facts(s: dict) -> str:
    facts = dict(s.get("visible_context") or {})
    env = s.get("initial_environment") or {}
    for k in ("outstanding_amount", "current_date", "payment_status"):
        if k in env:
            facts[k] = env[k]
    return json.dumps(facts, ensure_ascii=False, indent=1)


COMMON = """You are scoring one conversation between a debt-collection voice agent and a customer,
under the fixed rubric below. Score ONLY the metric named at the end. Return strict JSON:
{"rating": <int 1-5>, "evidence": [{"quote": "<verbatim>", "issue": "<short>"}], "explanation": "<2-3 sentences>"}
Every deduction needs a verbatim quote from the transcript or log. Do not judge whether the task
was completed; that is computed elsewhere. Language switching between Hindi, Hinglish and
English is not a fault unless it confused the caller.

=== RUBRIC (authoritative) ===
{rubric}
=== END RUBRIC ===
"""


def build_prompt(metric: str, conv: dict, prompts: dict) -> str:
    head = COMMON.replace("{rubric}", RUBRIC)
    ctx = [
        f"CALLER'S SCRIPTED GOAL: {conv['goal']}",
        f"ACCOUNT FACTS GIVEN TO THE AGENT:\n{conv['facts']}",
        f"REQUIRED ACTIONS FOR THIS SITUATION: {json.dumps(conv['required_full'], ensure_ascii=False)}",
        f"PERMANENT LOG, EVERY WRITE IN ORDER:\n{fmt_ledger(conv)}",
    ]
    if metric == "faithfulness":
        ctx.insert(0, f"AGENT INSTRUCTIONS (version under test):\n{prompts[conv['ver']]}")
    body = "\n\n".join(ctx)
    return (
        f"{head}\n{body}\n\nTRANSCRIPT:\n{fmt_transcript(conv['transcript'])}\n\n"
        f"METRIC TO SCORE NOW: {metric}. Apply that metric's five anchors exactly."
    )


BREAK_PROMPT = """You are locating the first breaking turn of a failed debt-collection call.
Definition: the earliest agent turn (T1, T2, ...) after which the required end state could no
longer be reached without correction. Return strict JSON:
{{"turn": <int, the T number>, "reason": "<max 20 words>"}}

REQUIRED ACTIONS: {req}
ACCEPTED DISPOSITIONS: {disp}
WHAT THE LOG ACTUALLY SHOWS:
{ledger}

TRANSCRIPT (agent turns numbered):
{transcript}
"""


# ---------------------------------------------------------------- judge calls


def call_gemini(key: str, prompt: str, attempt: int = 0) -> dict:
    req = urllib.request.Request(
        API.format(m=JUDGE_MODEL, k=key),
        data=json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
        }).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.loads(r.read())
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text)
        if isinstance(parsed, list):
            parsed = parsed[0] if parsed and isinstance(parsed[0], dict) else {}
        if not isinstance(parsed, dict):
            parsed = {}
        return {"ok": True, "raw": text, "parsed": parsed}
    except Exception as e:  # noqa: BLE001
        if attempt < 4:
            code = getattr(e, "code", None)
            time.sleep(min(60, 2 ** attempt * 3) if code in (429, 500, 503, None) else 2)
            return call_gemini(key, prompt, attempt + 1)
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def norm(rating: int) -> float:
    return round((max(1, min(5, int(rating))) - 1) / 4, 2)


# ---------------------------------------------------------------------- main


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--only", help="key prefix filter, e.g. phone-v4")
    args = ap.parse_args()

    key = load_env_key()
    scen = load_scenarios()
    prompts = load_prompts()
    convs = phone_conversations(scen) + bot_conversations(scen)
    if args.smoke:
        convs = [c for c in convs if c["key"] in ("phone-v3:card-08", "bot-v3:pay-now")]
    if args.only:
        convs = [c for c in convs if c["key"].startswith(args.only)]

    metrics = ("faithfulness", "conciseness", "conversation_progression")
    jobs = [(c, m) for c in convs for m in metrics]
    print(f"{len(convs)} conversations, {len(jobs)} judge calls")

    results: dict[str, dict] = {c["key"]: {} for c in convs}
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(call_gemini, key, build_prompt(m, c, prompts)): (c, m) for c, m in jobs}
        done = 0
        for fut in cf.as_completed(futs):
            c, m = futs[fut]
            r = fut.result()
            results[c["key"]][m] = r
            done += 1
            tag = r["parsed"].get("rating") if r.get("ok") else "ERR"
            print(f"  [{done}/{len(jobs)}] {c['key']} {m} -> {tag}", flush=True)

    # breaking turn: judged only where task failed and no deterministic dupe explains it
    for c in convs:
        if c["passed"]:
            continue
        p = BREAK_PROMPT.format(
            req=json.dumps(c["required_full"], ensure_ascii=False),
            disp=json.dumps(c["accepted"]),
            ledger=fmt_ledger(c),
            transcript=fmt_transcript(c["transcript"]),
        )
        r = call_gemini(key, p)
        results[c["key"]]["breaking_turn"] = r
        tag = r["parsed"] if r.get("ok") else "ERR"
        print(f"  break {c['key']} -> {tag}", flush=True)

    provenance = {
        "schema": "rescore.v1",
        "rubric": "rubric.v1",
        "judge_model": JUDGE_MODEL,
        "temperature": 0,
        "ran_at": datetime.now(UTC).isoformat(),
        "instructions_note": (
            "v3 judged against the deployed baseline prompt (gen1 seed); v4 against the gen2 "
            "champion text 667ce12e. The live v4 adds one declared closing patch (end_interaction "
            "naming) that touches no judged policy."
        ),
        "conversations": {
            c["key"]: {
                "scenario_id": c["scenario_ref"],
                "run_record": c.get("run_record"),
                "ledger_used": c["ledger"],
                "passed_task": c["passed"],
                "results": results[c["key"]],
            } for c in convs
        },
    }
    out = RESCORE / ("smoke.json" if args.smoke else "judge_scores.json")
    if args.only and out.exists():
        prior = json.loads(out.read_text())
        prior["conversations"].update(provenance["conversations"])
        prior["ran_at"] = provenance["ran_at"]
        provenance = prior
    out.write_text(json.dumps(provenance, ensure_ascii=False, indent=1))
    print(f"\nwrote {out}  ({time.time()-t0:.0f}s)")

    if args.smoke:
        for k, v in results.items():
            for m, r in v.items():
                print(f"\n=== {k} · {m} ===")
                print(json.dumps(r.get("parsed", r), ensure_ascii=False, indent=1)[:1200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
