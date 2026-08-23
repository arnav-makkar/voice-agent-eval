"""Reset and read the shared tool run between chat-pilot scenarios.

The deployed Indus tools pin run_id and account_id to fixed values (open issue
O1: the platform's agent-variable picker will not surface), so every scenario's
tool writes land on the same ledger row. Until per-run binding is solved, the
pilot runs strictly sequentially and this resets that row between scenarios so
each one still starts from a known state and is read in isolation.

Never use this while anything runs in parallel — it would silently corrupt both.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "artifacts" / "tool_service" / "tools.db"
RUN_ID = "c2-run-001"
ACCOUNT_ID = "EC-DEMO-4416"


def _blank(outstanding: str, account_id: str = ACCOUNT_ID) -> dict:
    return {
        "account_id": account_id,
        "payment_status": "unpaid",
        "outstanding_amount": outstanding,
        "promise_to_pay_date": None,
        "callback": None,
        "disposition": None,
        "dispute_reason": None,
        "escalation": None,
    }


def reset(outstanding: str, run_id: str = RUN_ID, account_id: str = ACCOUNT_ID) -> dict:
    """Return a run to its seeded state, creating it if it does not exist yet.

    Redialling a card has to be safe: the call sheet tells the caller to redial on
    a dropped line, and a half-finished attempt must not leave tool writes behind
    that get counted against the retry.
    """
    state = _blank(outstanding, account_id)
    blob = json.dumps(state)
    with sqlite3.connect(DB) as c:
        c.execute("DELETE FROM events WHERE run_id = ?", (run_id,))
        changed = c.execute(
            "UPDATE runs SET state_json = ?, initial_state_json = ? WHERE run_id = ?",
            (blob, blob, run_id),
        ).rowcount
        if not changed:
            now = __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat()
            c.execute("INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?)",
                      (run_id, account_id, blob, blob, now, now))
    return state


def read(run_id: str = RUN_ID) -> dict:
    with sqlite3.connect(DB) as c:
        row = c.execute("SELECT state_json FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        events = [
            {"tool": name, "arguments": json.loads(args)}
            for name, args in c.execute(
                "SELECT tool_name, arguments_json FROM events WHERE run_id = ? ORDER BY created_at",
                (run_id,),
            )
        ]
    return {"state": json.loads(row[0]) if row else None, "events": events}


if __name__ == "__main__":
    if sys.argv[1] == "reset":
        rid = sys.argv[3] if len(sys.argv) > 3 else RUN_ID
        acc = sys.argv[4] if len(sys.argv) > 4 else ACCOUNT_ID
        print(json.dumps(reset(sys.argv[2], rid, acc), ensure_ascii=False))
    else:
        rid = sys.argv[2] if len(sys.argv) > 2 else RUN_ID
        print(json.dumps(read(rid), ensure_ascii=False, indent=2))
