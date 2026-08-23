"""Append one chat-pilot scenario result and score it against the frozen truth.

Scoring here is deliberately narrow: disposition, required tool actions and
expected environment state, all read from the append-only tool ledger rather
than from anything the agent said. The transcript is preserved for review but
never scored, because a spoken claim is not a tool effect.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "artifacts" / "campaign2" / "chat_pilot" / "results.jsonl"


def score(scenario: dict, effects: dict) -> dict:
    state = effects.get("state") or {}
    called = [e["tool"] for e in effects.get("events", [])]
    required = list(scenario["required"])
    missing = [t for t in required if t not in called]
    disposition = state.get("disposition")
    checks = {
        "disposition": disposition in scenario["accept"],
        "required_actions": not missing,
        "environment_state": all(state.get(k) == v for k, v in (scenario.get("state") or {}).items()),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "observed_disposition": disposition,
        "tools_called": called,
        "tools_missing": missing,
        "first_failure": next((k for k, v in checks.items() if not v), None),
    }


if __name__ == "__main__":
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    row = {**payload, "result": score(payload["scenario"], payload["effects"])}
    with OUT.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps(row["result"], ensure_ascii=False, indent=2))
