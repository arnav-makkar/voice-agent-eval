"""Pull the champion's phone calls — transcript, audio, and ledger — per card.

Matching is by write containment, not by time proximity. Every card's journal
writes carry timestamps, and a write can only have happened while that card's
call was live — so the call for a card is the unique interaction whose time span
contains the card's writes. Two proximity heuristics failed before this design:
nearest-by-anchor matched one interaction to two cards, and earliest-in-window
grabbed a 9-second probe for card 1 and cascaded every later card off by one.

Recordings arrive as WAV despite the `.mp3` name the endpoint implies, so they
are transcoded once here. Tool truth comes from the local journal, never from the
transcript's `tools` field — the transcript is evidence of what was *said*.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from framework.evaluation.adapters.indus_text_chat import load_token  # noqa: E402
from scripts.call_context import _seeded_at, _started_at_utc  # noqa: E402
from scripts.fetch_call_logs import BASE, _get, list_interactions  # noqa: E402

SITE = ROOT.parent / "dashboard" / "public" / "evidence" / "audio" / "phone-v4"


def journal(run_id: str) -> list[str]:
    with sqlite3.connect(ROOT / "artifacts" / "tool_service" / "tools.db") as conn:
        return [r[0] for r in conn.execute(
            "SELECT tool_name FROM events WHERE run_id = ? ORDER BY created_at", (run_id,))]


def main() -> int:
    from datetime import datetime, timedelta

    token = load_token()
    cards = {c["card"]: c for c in json.loads(
        (ROOT / "artifacts" / "campaign2" / "phone" / "v4_15.json").read_text())["per_card"]}
    # The card's contract (which writes are required) lives in the baseline file;
    # v4_15.json records only what happened.
    contract = {c["card"]: list(c["required"]) + ["record_call_outcome"]
                for c in json.loads((ROOT / "artifacts" / "campaign2" / "phone" /
                                     "baseline_15.json").read_text())["per_card"]}
    SITE.mkdir(parents=True, exist_ok=True)

    def writes_for(run_id: str) -> list:
        with sqlite3.connect(ROOT / "artifacts" / "tool_service" / "tools.db") as conn:
            return [datetime.fromisoformat(r[0]) for r in conn.execute(
                "SELECT created_at FROM events WHERE run_id = ? ORDER BY created_at",
                (run_id,))]

    index = []
    with httpx.Client(follow_redirects=True) as client:
        pool = {}
        for card in sorted(cards):
            seeded = _seeded_at(f"c2-phone-{card:02d}-v4")
            if seeded is None:
                continue
            lo = (seeded - timedelta(minutes=6)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            hi = (seeded + timedelta(minutes=6)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            for it in list_interactions(client, token, lo, hi, "v2v"):
                if (it.get("duration_in_seconds") or 0) >= 8:
                    pool[it["interaction_id"]] = it

        assigned, taken = {}, set()
        for card in sorted(cards):
            stamps = writes_for(f"c2-phone-{card:02d}-v4")
            if not stamps:
                print(f"  card {card:2}: no journal writes — cannot match, skipped")
                continue
            hits = []
            for it in pool.values():
                start = _started_at_utc(it)
                end = start + timedelta(seconds=(it.get("duration_in_seconds") or 0) + 90)
                if all(start - timedelta(seconds=15) <= w <= end for w in stamps):
                    hits.append(it)
            hits = [h for h in hits if h["interaction_id"] not in taken]
            if not hits:
                print(f"  card {card:2}: no interaction contains its writes — skipped")
                continue
            if len(hits) > 1:  # overlapping spans; take the tightest containment
                hits.sort(key=lambda it: abs((stamps[0] - _started_at_utc(it)).total_seconds()))
            assigned[card] = hits[0]
            taken.add(hits[0]["interaction_id"])

        for card, item in assigned.items():
            spec = cards[card]
            run = f"c2-phone-{card:02d}-v4"
            iid = item["interaction_id"]
            turns = _get(client, f"{BASE}/interactions/{quote(iid, safe='/:')}"
                                 f"/transcript?translate=false", token).json().get("transcript", [])
            audio = _get(client, f"{BASE}/interactions/{quote(iid, safe='/:')}"
                                 f"/merged-audio", token)

            mp3 = SITE / f"card-{card:02d}.mp3"
            if audio.status_code == 200 and audio.content:
                raw = SITE / f"card-{card:02d}.raw"
                raw.write_bytes(audio.content)
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw),
                                "-codec:a", "libmp3lame", "-b:a", "96k", str(mp3)], check=True)
                raw.unlink()

            index.append({
                "id": f"card-{card:02d}",
                "tier": "phone",
                "version": "v4 champion",
                "title": f"Card {card} · {spec['family'].replace('_', ' ')}",
                "card": card,
                "family": spec["family"],
                "interaction_id": iid,
                "started": item.get("start_datetime"),
                "duration_s": item.get("duration_in_seconds"),
                "end_reason": item.get("end_reason"),
                "tools": journal(run),          # journal is the only tool evidence
                "required": contract[card],
                "missing": spec["missing"],
                "duplicate_writes": spec["duplicates"],
                "exactly_once": spec["exactly_once"],
                "passed": spec["v4"],
                "v3_passed": spec["v3"],
                "transcript": [
                    {"speaker": "agent" if t.get("role") == "assistant" else "caller",
                     "text": (t.get("content") or "").strip()}
                    for t in turns if (t.get("content") or "").strip()
                ],
                "audio": f"/evidence/audio/phone-v4/card-{card:02d}.mp3" if mp3.exists() else None,
            })
            print(f"  card {card:2} {spec['family']:26} {item.get('duration_in_seconds'):5.1f}s "
                  f"{item.get('end_reason'):11} {len(turns):2} turns "
                  f"{'audio' if mp3.exists() else 'NO AUDIO'}")

    iids = [c["interaction_id"] for c in index]
    assert len(iids) == len(set(iids)), "an interaction was assigned to two cards"
    (SITE / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1))
    agent_ends = sum(1 for c in index if c["end_reason"] == "AGENT_ENDS")
    print(f"\n  {len(index)} calls staged -> {SITE}")
    print(f"  agent hung up on {agent_ends}/{len(index)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
