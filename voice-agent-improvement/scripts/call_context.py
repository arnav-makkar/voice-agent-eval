"""Read how a phone call ended, from Sarvam's own analytics.

The journal says what the agent *did*. It cannot say whether the agent ever got
the chance: a call where the customer hangs up mid-sentence and a call where the
agent said goodbye and wrote nothing leave the same empty space in the ledger,
and they are not the same result.

`end_reason` and the agent's last spoken turn together separate them:

    USER_ENDS  + last agent turn still mid-negotiation -> no chance, inconclusive
    USER_ENDS  + last agent turn is a closing line     -> had the chance, failed
    AGENT_ENDS                                         -> always had the chance

Only the second and third count against the agent. The transcript is used here to
decide whether the agent had an *opportunity*, never to decide whether a tool ran
— that stays with the journal, as everywhere else in this framework.
"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import quote

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Analytics filters on UTC but renders start_datetime in IST, so a window built
# from local wall-clock silently misses the most recent calls. Reach back far
# enough that the offset cannot hide them.
LOOKBACK_HOURS = 18


IST_OFFSET_HOURS = 5.5  # analytics renders start_datetime in IST, filters in UTC


def _seeded_at(run_id: str):
    """When this card was last dialled.

    `created_at` is the row's *first* seed and never moves, so a redialled card
    would resolve to its original attempt — card 1 kept pointing at the call that
    still had the platform nudge in it, long after the redial fixed that. The
    latest of the two timestamps is the one that tracks the most recent dial.
    """
    import sqlite3
    from datetime import datetime

    with sqlite3.connect(ROOT / "artifacts" / "tool_service" / "tools.db") as conn:
        row = conn.execute("SELECT created_at, updated_at FROM runs WHERE run_id = ?",
                           (run_id,)).fetchone()
    if not row:
        return None
    return max(datetime.fromisoformat(t) for t in row if t)


def _started_at_utc(item: dict):
    """`start_datetime` as UTC. It arrives as IST wall-clock, e.g. 'Aug 24, 2026, 01:08:48 AM'."""
    from datetime import datetime, timedelta, timezone

    stamp = datetime.strptime(item["start_datetime"], "%b %d, %Y, %I:%M:%S %p")
    return (stamp - timedelta(hours=IST_OFFSET_HOURS)).replace(tzinfo=timezone.utc)


def last_call_context(run_id: str | None = None) -> dict:
    """End reason and last agent turn for the call placed against `run_id`.

    Matched by time, not by recency: the analytics API never sees the ledger key,
    so the call for a card is the first interaction to start after that card's
    ledger row was seeded. Taking the newest call instead attributes whatever was
    dialled last to every card scored afterwards.
    """
    from datetime import datetime, timedelta, timezone

    from framework.evaluation.adapters.indus_text_chat import load_token
    from scripts.fetch_call_logs import BASE, _get, list_interactions

    token = load_token()
    seeded = _seeded_at(run_id) if run_id else None

    # Anchor the window on the seed, not on "the last N hours". The report returns
    # page 1 of an ascending sort with no pagination here, so a wide window fills
    # that page with the oldest interactions and the call we want never appears —
    # an 18-hour lookback silently returned only the previous morning's runs.
    # The anchor is the last activity on the row, which may be a tool write from
    # part-way through the call rather than the seed that preceded it. Reach back
    # far enough to include the call's start, then take the nearest interaction.
    if seeded is not None:
        lo, hi = seeded - timedelta(minutes=6), seeded + timedelta(minutes=6)
    else:
        now = datetime.now(timezone.utc)
        lo, hi = now - timedelta(hours=LOOKBACK_HOURS), now + timedelta(hours=1)
    start = lo.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    end = hi.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    with httpx.Client(follow_redirects=True) as client:
        items = [
            item for item in list_interactions(client, token, start, end, "v2v")
            if (item.get("duration_in_seconds") or 0) >= 8
        ]
        if not items:
            raise RuntimeError(
                f"no voice interaction between {start} and {end} — "
                f"no call appears to have been placed for {run_id}")
        if seeded is None:
            item = items[-1]
        else:
            item = min(items, key=lambda i: abs((_started_at_utc(i) - seeded).total_seconds()))
            gap = abs((_started_at_utc(item) - seeded).total_seconds())
            if gap > 360:
                raise RuntimeError(
                    f"nearest call is {gap/60:.0f} min from {run_id}'s last activity "
                    f"— no call appears to have been placed for this card")
        turns = _get(
            client,
            f"{BASE}/interactions/{quote(item['interaction_id'], safe='/:')}"
            f"/transcript?translate=false",
            token,
        ).json().get("transcript", [])

    agent_turns = [
        (t.get("content") or "").strip()
        for t in turns
        if t.get("role") == "assistant" and (t.get("content") or "").strip()
    ]
    return {
        "run_id": run_id,
        "interaction_id": item["interaction_id"],
        "end_reason": item.get("end_reason"),
        "duration_s": item.get("duration_in_seconds"),
        "last_agent_turn": agent_turns[-1] if agent_turns else None,
        "turns": len(turns),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(last_call_context(*sys.argv[1:2]), ensure_ascii=False, indent=1))
