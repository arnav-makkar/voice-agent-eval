"""A reused event_id silently replays the first result and writes nothing.

The tool service treats ``event_id`` as an idempotency key, which is correct for
a real integration: a retried webhook must not double-record a payment. But the
Indus tool config sent a hard-coded ``evt-1`` on every call, which turned that
safeguard into silent data loss — the first tool call of a campaign persisted
and every later one returned the first call's stored result with a 200.

It was invisible for exactly the wrong reason: the platform reported success,
the journal recorded a well-formed request, and only the ledger disagreed. The
chat pilot appeared to work solely because its per-scenario reset deleted the
event row each time.

These tests pin both halves: that a repeated id replays, and that omitting the
id lets every call record independently.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from framework.tool_service import SeedRun, ToolStore


def _store(tmp: str) -> ToolStore:
    store = ToolStore(Path(tmp) / "t.db")
    store.seed(SeedRun(run_id="run-1", account_id="acct-1", outstanding_amount="100"))
    return store


class _Ctx:
    """Minimal stand-in for the request models' shared context fields."""

    def __init__(self, event_id: str | None) -> None:
        self.run_id = "run-1"
        self.account_id = "acct-1"
        self.event_id = event_id


def _record(store: ToolStore, ctx: _Ctx, disposition: str) -> dict:
    def mutate(state: dict) -> dict:
        state["disposition"] = disposition
        return {"recorded": True, "disposition": disposition}

    return store.execute(
        context=ctx, tool_name="record_call_outcome",
        arguments={"disposition": disposition}, mutate=mutate,
    )


class EventIdReplayTest(unittest.TestCase):
    def test_a_reused_event_id_replays_and_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            _record(store, _Ctx("evt-1"), "rtp")
            second = _record(store, _Ctx("evt-1"), "fptp")
            # The caller asked for fptp and was told rtp, with no error raised.
            self.assertEqual(second["disposition"], "rtp")
            self.assertEqual(store.read("run-1")["state"]["disposition"], "rtp")
            self.assertEqual(len(store.read("run-1")["events"]), 1)

    def test_omitting_the_event_id_lets_every_call_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            _record(store, _Ctx(None), "acknowledged")
            second = _record(store, _Ctx(None), "dispute")
            self.assertEqual(second["disposition"], "dispute")
            self.assertEqual(store.read("run-1")["state"]["disposition"], "dispute")
            self.assertEqual(len(store.read("run-1")["events"]), 2)

    def test_distinct_event_ids_still_deduplicate_a_genuine_retry(self) -> None:
        # Idempotency must survive the fix — it is only the fixed id that broke.
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            _record(store, _Ctx("a"), "rtp")
            _record(store, _Ctx("b"), "callback")
            replay = _record(store, _Ctx("a"), "dispute")
            self.assertEqual(replay["disposition"], "rtp")
            self.assertEqual(len(store.read("run-1")["events"]), 2)


if __name__ == "__main__":
    unittest.main()
