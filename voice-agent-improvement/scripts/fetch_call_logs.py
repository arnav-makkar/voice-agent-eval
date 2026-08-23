"""Pull transcripts and recordings for real calls from the Indus analytics API.

The phone tier was recorded by a human on a real handset, so the only record of
what was said lives on Sarvam's side. Three endpoints, discovered by capturing
the analytics console's own traffic:

    GET .../analytics/v4/orgs/{org}/workspaces/{ws}/unified-report?...
        -> one row per interaction: id, duration, start/end, end_reason
    GET .../interactions/{interaction_id}/transcript?translate=false
        -> [{role, content, tools, audio_start_time, audio_end_time, ...}]
    GET .../interactions/{interaction_id}/merged-audio
        -> the call recording (404 for text-chat interactions, which have none)

Two properties worth keeping:

* Transcripts are evidence of what was *said*. They are never used to decide
  whether a tool ran — that stays with the journal, exactly as in every other
  tier. A transcript here is for the reader, and for the speech-quality metrics
  that cannot be computed without one.
* ``merged-audio`` legitimately 404s on chat interactions. That is recorded as
  "no recording" rather than treated as a failure, so a missing file never
  masquerades as a broken fetch.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.parse import quote

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from framework.evaluation.adapters.indus_text_chat import (  # noqa: E402
    APP,
    ORG,
    WORKSPACE,
    load_token,
)

BASE = f"https://apps.sarvam.ai/api/analytics/v4/orgs/{ORG}/workspaces/{WORKSPACE}"
OUT = ROOT / "artifacts" / "campaign2" / "phone" / "recordings"


def _get(client: httpx.Client, url: str, token: str, attempts: int = 4):
    """GET with backoff. apps.sarvam.ai intermittently drops the TLS handshake;
    a timeout is a transport event, never evidence about the call."""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json, */*"}
    last = None
    for attempt in range(attempts):
        try:
            return client.get(url, headers=headers, timeout=90)
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(4 * (attempt + 1))
    raise RuntimeError(f"unreachable after {attempts} attempts: {last}")


def list_interactions(client, token, start_iso, end_iso, channel="v2v") -> list[dict]:
    url = (f"{BASE}/unified-report?app_id={APP}&sort_by=effective_datetime"
           f"&sort_order=asc&channel_type={channel}"
           f"&start_datetime={quote(start_iso)}&end_datetime={quote(end_iso)}"
           f"&campaign_id=all_campaigns&page=1&page_size=200")
    response = _get(client, url, token)
    response.raise_for_status()
    return response.json().get("items", [])


def transcript(client, token, interaction_id: str) -> list[dict]:
    url = f"{BASE}/interactions/{quote(interaction_id, safe='/:')}/transcript?translate=false"
    response = _get(client, url, token)
    if response.status_code != 200:
        return []
    return response.json().get("transcript", [])


def recording(client, token, interaction_id: str) -> bytes | None:
    """The merged call audio, or None when the interaction has no recording."""
    url = f"{BASE}/interactions/{quote(interaction_id, safe='/:')}/merged-audio"
    response = _get(client, url, token)
    if response.status_code != 200 or not response.content:
        return None
    body = response.content
    # Some deployments hand back a JSON envelope carrying a signed URL rather
    # than the bytes themselves.
    if body[:1] in (b"{", b"["):
        try:
            payload = json.loads(body)
        except Exception:  # noqa: BLE001
            return None
        link = payload.get("url") or payload.get("signed_url") or payload.get("audio_url")
        if not link:
            return None
        follow = _get(client, link, token)
        return follow.content if follow.status_code == 200 else None
    return body


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2026-08-22T00:00:00.000Z")
    parser.add_argument("--end", default="2026-08-24T00:00:00.000Z")
    parser.add_argument("--channel", default="v2v", help="v2v = voice, t2t = text chat")
    parser.add_argument("--min-duration", type=float, default=15.0,
                        help="skip interactions shorter than this (probes, misdials)")
    parser.add_argument("--list-only", action="store_true")
    parser.add_argument("--outbound-only", action="store_true",
                        help="keep only real outbound telephony (the human phone tier)")
    args = parser.parse_args()

    token = load_token()
    OUT.mkdir(parents=True, exist_ok=True)
    with httpx.Client(follow_redirects=True) as client:
        items = list_interactions(client, token, args.start, args.end, args.channel)
        items = [i for i in items if (i.get("duration_in_seconds") or 0) >= args.min_duration]
        if args.outbound_only:
            # The phone tier is outbound telephony to a real handset. Inbound rows
            # are the bot-to-bot websocket sessions and the browser debug tests,
            # which have their own artifacts already.
            items = [i for i in items
                     if i.get("channel_direction") == "outbound"
                     and not i.get("is_debug_call")]
        print(f"  {len(items)} interactions >= {args.min_duration}s on channel {args.channel}")
        for index, item in enumerate(items, 1):
            print(f"    {index:2}. {item.get('start_datetime')}  "
                  f"{item.get('duration_in_seconds'):6.1f}s  "
                  f"{item.get('end_reason')}  msgs={item.get('num_messages')}  "
                  f"{item.get('interaction_id')}")
        if args.list_only:
            return 0

        saved = 0
        for index, item in enumerate(items, 1):
            iid = item["interaction_id"]
            turns = transcript(client, token, iid)
            audio = recording(client, token, iid)
            slug = f"call-{index:02d}"
            if audio:
                (OUT / f"{slug}.mp3").write_bytes(audio)
            (OUT / f"{slug}.json").write_text(json.dumps({
                "slug": slug,
                "interaction_id": iid,
                "start": item.get("start_datetime"),
                "duration_s": item.get("duration_in_seconds"),
                "end_reason": item.get("end_reason"),
                "language": item.get("language_name"),
                "num_messages": item.get("num_messages"),
                "channel_direction": item.get("channel_direction"),
                "has_recording": bool(audio),
                "transcript": [
                    {"speaker": "agent" if t.get("role") == "assistant" else "caller",
                     "text": (t.get("content") or "").strip(),
                     "tools": t.get("tools")}
                    for t in turns if (t.get("content") or "").strip()
                ],
            }, ensure_ascii=False, indent=1))
            saved += 1
            print(f"    saved {slug}: {len(turns)} turns, "
                  f"{'audio ' + str(round(len(audio)/1024)) + 'kb' if audio else 'no recording'}")
        print(f"  wrote {saved} interactions -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
