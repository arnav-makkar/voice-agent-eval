"""Rank every observed failure into one taxonomy across all three tiers.

Text, phone and bot-to-bot failures are ranked together rather than in separate
per-tier reports, because the improvement round has to spend its effort on what
is actually costing the most, and that ordering is invisible while each tier
keeps its own scoreboard.

Every packet carries the evidence that produced it — scenario id, the tier it was
seen in, and what the journal did or did not record — so a proposed fix can be
checked against a real conversation instead of a summary.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAT = ROOT / "artifacts" / "campaign2" / "chat_bulk"
BOT = ROOT / "artifacts" / "campaign2" / "bot_to_bot" / "pilot_5.json"
OUT = ROOT / "artifacts" / "campaign2" / "diagnosis" / "taxonomy_v2.json"

# Defects named from the 15 recorded phone calls. They are carried in by hand
# because that tier is human-run and its labels are owner-confirmed, not derived.
PHONE_DEFECTS = [
    {"id": "P1", "tier": "phone", "title": "Handles the substance but records nothing",
     "detail": "Agent resolves the caller's request in conversation and never calls "
               "record_call_outcome, so the call leaves no trace in the journal.",
     "evidence": ["card 5", "card 6"], "severity": "critical"},
    {"id": "P2", "tier": "phone", "title": "Fraud claim filed as refusal-to-pay",
     "detail": "A fraud allegation was recorded as rtp and collection continued, "
               "instead of escalate_to_human and stopping the ask.",
     "evidence": ["card 11"], "severity": "critical"},
    {"id": "P3", "tier": "phone", "title": "Escalation recorded without escalating",
     "detail": "disposition=escalation written while escalate_to_human was never called, "
               "so nothing was actually routed to a human.",
     "evidence": ["card 12"], "severity": "critical"},
    {"id": "P4", "tier": "phone", "title": "Relative time never becomes a date",
     "detail": "'agle hafte' and similar are acknowledged but never resolved into a "
               "DD-MM-YYYY argument, so no promise is recorded.",
     "evidence": ["card 3"], "severity": "high"},
    {"id": "P5", "tier": "phone", "title": "Answers ledger questions from memory",
     "detail": "Answers a payment-status question from the prompt's account block "
               "instead of calling check_payment_status.",
     "evidence": ["card 13"], "severity": "medium"},
    {"id": "P6", "tier": "phone", "title": "Does not end the call",
     "detail": "Agent keeps the line open after the outcome is settled.",
     "evidence": ["all cards"], "severity": "medium"},
]


def load_chat(version: int) -> list[dict]:
    rows: list[dict] = []
    for split in ("development", "validation", "regression"):
        path = CHAT / f"v{version}_{split}.jsonl"
        if path.exists():
            rows += [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    return rows


def chat_packets(rows: list[dict]) -> list[dict]:
    """Turn failing chat conversations into ranked packets."""
    by_reason: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grade = row["grade"]
        if grade["passed"]:
            continue
        if row.get("error"):
            by_reason["transport_error"].append(row)
            continue
        for missing in grade["missing_required"]:
            name = missing.split("{")[0]
            # A required action can fail two ways, and they need different fixes.
            # If the tool never fired, the agent did not recognise the situation.
            # If it fired but the contract still counts it missing, the arguments
            # were wrong — a dispute filed as `acknowledged`, a refusal filed as
            # `ptp_today` — which is worse than silence, because it puts a
            # commitment in the ledger the customer never made.
            fired = any(e.get("tool") == name for e in row.get("journal_events") or [])
            key = f"{name}:wrong_arguments" if fired else f"{name}:never_called"
            by_reason[key].append(row)
        if not grade["disposition_ok"] and not grade["missing_required"]:
            by_reason[f"wrong_disposition:{grade['disposition']}"].append(row)

    packets = []
    for reason, hits in sorted(by_reason.items(), key=lambda kv: -len(kv[1])):
        families = Counter(h["family"] for h in hits)
        packets.append({
            "id": f"C{len(packets)+1}",
            "tier": "chat",
            "reason": reason,
            "count": len(hits),
            "families": families.most_common(5),
            "languages": Counter(h["language"] for h in hits).most_common(),
            "evidence": [h["scenario_id"] for h in hits[:6]],
            "sample_transcript": hits[0]["transcript"][:900],
        })
    return packets


def bot_packets() -> list[dict]:
    if not BOT.exists():
        return []
    data = json.loads(BOT.read_text())
    packets = []
    for call in data["calls"]:
        tools = call["ledger"]["tools"]
        dupes = [t for t, n in Counter(tools).items() if n > 1]
        if dupes:
            packets.append({
                "id": f"B{len(packets)+1}", "tier": "bot_to_bot",
                "reason": "duplicate_tool_write", "count": len(dupes),
                "evidence": [call["record_id"]], "detail": f"wrote {dupes} more than once",
            })
    return packets


def main() -> int:
    rows = load_chat(3)
    packets = chat_packets(rows)
    packets += bot_packets()
    packets += [dict(p, count=len(p["evidence"])) for p in PHONE_DEFECTS]

    total = len(rows)
    passed = sum(1 for r in rows if r["grade"]["passed"])
    summary = {
        "chat_base": {"n": total, "passed": passed,
                      "rate": round(passed / total, 3) if total else None},
        "by_split": {
            split: {
                "n": sum(1 for r in rows if r["split"] == split),
                "passed": sum(1 for r in rows if r["split"] == split and r["grade"]["passed"]),
            } for split in ("development", "validation", "regression")
        },
        "by_family": sorted(
            [{"family": f,
              "n": sum(1 for r in rows if r["family"] == f),
              "passed": sum(1 for r in rows if r["family"] == f and r["grade"]["passed"])}
             for f in {r["family"] for r in rows}],
            key=lambda d: (d["passed"] / d["n"]) if d["n"] else 1),
        "by_language": sorted(
            [{"language": g,
              "n": sum(1 for r in rows if r["language"] == g),
              "passed": sum(1 for r in rows if r["language"] == g and r["grade"]["passed"])}
             for g in {r["language"] for r in rows}],
            key=lambda d: (d["passed"] / d["n"]) if d["n"] else 1),
        "packets": packets,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2))

    print(f"  chat BASE: {passed}/{total}")
    for split, s in summary["by_split"].items():
        if s["n"]:
            print(f"    {split:12} {s['passed']}/{s['n']}")
    print("  weakest families:")
    for fam in summary["by_family"][:6]:
        print(f"    {fam['family']:26} {fam['passed']}/{fam['n']}")
    print("  packets:")
    for p in packets[:10]:
        print(f"    {p['id']:4} {p['tier']:11} {p.get('reason') or p.get('title')} × {p['count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
