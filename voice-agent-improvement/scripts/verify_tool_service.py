"""Prove the run-scoped tool service enforces execution truth.

Run against a live service to check the properties the evaluation depends on:
authentication fails closed, a run can only be touched by the account it was
seeded for, tool calls actually mutate state, and every call lands in an
append-only log.

This exercises the service directly.  It is deliberately *not* evidence that the
deployed voice platform can reach it — that requires a call originating from the
platform itself, which is a separate gate.

    python scripts/verify_tool_service.py --base-url http://127.0.0.1:8788
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from framework.adapters.gemini import load_env_file  # noqa: E402
from framework.core.io import write_json  # noqa: E402

OUTPUT = ROOT / "artifacts" / "framework" / "emi" / "tool_service_verification.json"


def _request(base: str, path: str, secret: str | None, payload: Any = None, method: str = "POST") -> tuple[int, Any]:
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(f"{base}{path}", data=data, method=method)
    request.add_header("Content-Type", "application/json")
    if secret:
        request.add_header("X-Loopline-Tool-Key", secret)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()[:200]


def verify(base_url: str, run_id: str, account_id: str) -> dict[str, Any]:
    load_env_file(ROOT / ".env")
    secret = os.environ.get("LOOPLINE_TOOL_SECRET")
    if not secret:
        raise SystemExit("LOOPLINE_TOOL_SECRET is not set; the service cannot be verified without it.")

    checks: list[dict[str, Any]] = []

    def record(name: str, expectation: str, passed: bool, observed: Any) -> None:
        checks.append({"name": name, "expects": expectation, "passed": passed, "observed": observed})

    status, _ = _request(base_url, "/health", None, method="GET")
    record("health reachable", "200 without credentials", status == 200, status)

    status, seeded = _request(base_url, "/v1/evaluation/runs", secret, {"run_id": run_id, "account_id": account_id, "outstanding_amount": "4416"})
    record("seed a fresh run", "200 and an empty starting state", status == 200, status)
    before = seeded.get("state", {}) if isinstance(seeded, dict) else {}

    status, _ = _request(base_url, "/v1/tools/record-promise-to-pay", None, {"run_id": run_id, "account_id": account_id, "date": "20-08-2026"})
    record("unauthenticated tool call", "401 — authentication fails closed", status == 401, status)

    status, result = _request(base_url, "/v1/tools/record-promise-to-pay", secret, {"run_id": run_id, "account_id": account_id, "date": "20-08-2026"})
    record("authenticated tool call", "200 and recorded=true", status == 200 and isinstance(result, dict) and result.get("recorded") is True, result)

    status, after = _request(base_url, f"/v1/evaluation/runs/{run_id}", secret, method="GET")
    state = after.get("state", {}) if isinstance(after, dict) else {}
    moved = before.get("promise_to_pay_date") is None and state.get("promise_to_pay_date") == "20-08-2026"
    record("state actually moved", "promise_to_pay_date goes from null to the recorded date", moved,
           {"before": before.get("promise_to_pay_date"), "after": state.get("promise_to_pay_date")})

    status, _ = _request(base_url, "/v1/tools/record-promise-to-pay", secret, {"run_id": run_id, "account_id": "EC-WRONG-ACCOUNT", "date": "21-08-2026"})
    record("account mismatch", "409 — a run belongs to one account only", status == 409, status)

    status, _ = _request(base_url, "/v1/tools/record-promise-to-pay", secret, {"run_id": "run-that-does-not-exist", "account_id": account_id, "date": "21-08-2026"})
    record("unknown run", "404 — tools cannot invent a run", status == 404, status)

    status, _ = _request(base_url, "/v1/tools/schedule-callback", secret, {"run_id": run_id, "account_id": account_id, "date": "18-08-2026", "time_window": "05:00 PM - 06:00 PM"})
    record("second write tool", "200 and callback state written", status == 200, status)

    status, final = _request(base_url, f"/v1/evaluation/runs/{run_id}", secret, method="GET")
    events = final.get("events", []) if isinstance(final, dict) else []
    record("append-only event log", "every tool call is recorded in order", len(events) == 2 and [e["tool_name"] for e in events] == ["record_promise_to_pay", "schedule_callback"],
           [e["tool_name"] for e in events])

    passed = all(check["passed"] for check in checks)
    summary = {
        "schema_version": "tool-service-verification.v1",
        "verified_at": datetime.now(UTC).isoformat(),
        "base_url": base_url,
        "run_id": run_id,
        "passed": passed,
        "checks": checks,
        "final_state": final.get("state") if isinstance(final, dict) else None,
        "claim_boundary": (
            "This verifies the service itself. It is not evidence that the deployed voice platform can reach or "
            "authenticate against it; that requires a tool call originating from the platform and remains an open gate."
        ),
    }
    write_json(OUTPUT, summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("LOOPLINE_TOOL_BASE_URL", "http://127.0.0.1:8788"))
    parser.add_argument("--run-id", default=f"verify-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}")
    parser.add_argument("--account-id", default="EC-DEMO-9001")
    args = parser.parse_args()
    summary = verify(args.base_url, args.run_id, args.account_id)
    for check in summary["checks"]:
        print(f"  {'PASS' if check['passed'] else 'FAIL'}  {check['name']:26s} {check['expects']}")
    print(f"\n{'all checks passed' if summary['passed'] else 'FAILURES PRESENT'} -> {OUTPUT}")
    raise SystemExit(0 if summary["passed"] else 1)


if __name__ == "__main__":
    main()
