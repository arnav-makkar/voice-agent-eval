"""Pull the champion's phone calls — transcript, audio, and ledger — per card.

The analytics API never sees the ledger key, so a call is matched to a card by
time: each card's ledger row records when it was seeded, and the call is the
interaction that starts nearest that moment. `call_context` owns that matching
and its caveats; this script reuses it rather than re-deriving it.

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

OUT = ROOT / "dashboard_evidence" / "phone-v4"
SITE = ROOT.parent / "dashboard" / "public" / "evidence" / "audio" / "phone-v4"


def journal(run_id: str) -> list[str]:
    with sqlite3.connect(ROOT / "artifacts" / "tool_service" / "tools.db") as conn:
        return [r[0] for r in conn.execute(
            "SELECT tool_name FROM events WHERE run_id = ? ORDER BY created_at", (run_id,))]


def main() -> int:
    from datetime import timedelta

    token = load_token()
    cards = {c["card"]: c for c in json.loads(
        (ROOT / "artifacts" / "campaign2" / "phone" / "v4_15.json").read_text())["per_card"]}
    SITE.mkdir(parents=True, exist_ok=True)

    index = []
    with httpx.Client(follow_redirects=True) as client:
        for card in sorted(cards):
            spec = cards[card]
            run = f"c2-phone-{card:02d}-v4"
            seeded = _seeded_at(run)
            if seeded is None:
                print(f"  card {card:2}: never seeded — skipped")
                continue

            lo = (seeded - timedelta(minutes=6)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            hi = (seeded + timedelta(minutes=6)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            items = [i for i in list_interactions(client, token, lo, hi, "v2v")
                     if (i.get("duration_in_seconds") or 0) >= 8]
            if not items:
                print(f"  card {card:2}: no interaction near seed — skipped")
                continue
            item = min(items, key=lambda i: abs((_started_at_utc(i) - seeded).total_seconds()))

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
                "title": f"{spec['family'].replace('_', ' ')} · v4",
                "card": card,
                "family": spec["family"],
                "duration_s": item.get("duration_in_seconds"),
                "end_reason": item.get("end_reason"),
                "tools": journal(run),          # journal is the only tool evidence
                "required": list(spec["missing"]) + spec["tools"],
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

    (SITE / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1))
    agent_ends = sum(1 for c in index if c["end_reason"] == "AGENT_ENDS")
    print(f"\n  {len(index)} calls staged -> {SITE}")
    print(f"  agent hung up on {agent_ends}/{len(index)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
