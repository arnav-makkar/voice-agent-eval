"""Label-free say-versus-do invariants over the tool journal.

The benchmark can grade a conversation because it knows the script. Production
has no script — but most of the defects this campaign found are visible in the
journal *alone*, as internal inconsistencies between what the agent recorded:

  I1  disposition in {fptp, ptp_today}  but no record_promise_to_pay row
  I2  disposition == callback           but no schedule_callback row
  I3  disposition == escalation         but no escalate_to_human row
  I4  disposition == dispute            but no record_dispute row
  I5  a business write exists           but no record_call_outcome at all
  I6  the same write repeated           (duplicate tool rows, same args)
  I7  promise recorded with a date not in DD-MM-YYYY, or in the past

No transcript, no ground truth, no QA label is needed for any of them. That is
the production story for the improvement loop: these run nightly over the live
journal, violations become the failure packets, and the same GEPA loop consumes
them — the only benchmark-only ingredient is the scripted caller.

This audit runs the invariants over every recorded conversation and reports how
much of the benchmark-graded failure set they recover, which is the honest
measure of how well the loop would see in production.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BULK = ROOT / "artifacts" / "campaign2" / "chat_bulk"
OUT = ROOT / "artifacts" / "campaign2" / "improvement" / "invariant_audit.json"

PROMISE_DISPOSITIONS = {"fptp", "ptp_today"}
DATE_RE = re.compile(r"^\d{2}-\d{2}-\d{4}$")
TODAY = datetime(2026, 8, 22)


def violations(events: list[dict], disposition: str | None) -> list[str]:
    tools = [e.get("tool") for e in events]
    args = {e.get("tool"): (e.get("arguments") or {}) for e in events}
    found: list[str] = []

    if disposition in PROMISE_DISPOSITIONS and "record_promise_to_pay" not in tools:
        found.append("I1_promise_disposition_without_promise_row")
    if disposition == "callback" and "schedule_callback" not in tools:
        found.append("I2_callback_disposition_without_booking")
    if disposition == "escalation" and "escalate_to_human" not in tools:
        found.append("I3_escalation_disposition_without_escalation")
    if disposition == "dispute" and "record_dispute" not in tools:
        found.append("I4_dispute_disposition_without_dispute_row")
    business = {"record_promise_to_pay", "schedule_callback", "record_dispute",
                "escalate_to_human"} & set(tools)
    if business and "record_call_outcome" not in tools:
        found.append("I5_business_write_without_outcome")

    seen: Counter = Counter()
    for event in events:
        key = (event.get("tool"), json.dumps(event.get("arguments") or {}, sort_keys=True))
        seen[key] += 1
    if any(count > 1 for count in seen.values()):
        found.append("I6_duplicate_write")

    promise = args.get("record_promise_to_pay")
    if promise:
        date = str(promise.get("date", ""))
        if not DATE_RE.match(date):
            found.append("I7_malformed_promise_date")
        else:
            try:
                if datetime.strptime(date, "%d-%m-%Y") < TODAY:
                    found.append("I7_promise_date_in_past")
            except ValueError:
                found.append("I7_malformed_promise_date")
    return found


def main() -> int:
    report: dict = {"versions": {}}
    for version in ("v3", "v4", "v5", "g1", "g2"):
        rows = []
        for path in sorted(BULK.glob(f"{version}_*.jsonl")):
            rows += [json.loads(l) for l in path.read_text().splitlines() if l.strip()]

        flagged, benchmark_failed, both = [], [], []
        counts: Counter = Counter()
        for row in rows:
            found = violations(row.get("journal_events") or [],
                               row["grade"].get("disposition"))
            failed = not row["grade"].get("passed_env", row["grade"]["passed"])
            if found:
                flagged.append(row["scenario_id"])
                for v in found:
                    counts[v] += 1
            if failed:
                benchmark_failed.append(row["scenario_id"])
            if found and failed:
                both.append(row["scenario_id"])

        n = len(rows)
        report["versions"][version] = {
            "conversations": n,
            "invariant_flagged": len(flagged),
            "benchmark_failed": len(benchmark_failed),
            "flagged_and_failed": len(both),
            "recall_of_failures": round(len(both) / len(benchmark_failed), 3)
                if benchmark_failed else None,
            "precision_of_flags": round(len(both) / len(flagged), 3) if flagged else None,
            "violation_counts": dict(counts.most_common()),
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))
    for version, r in report["versions"].items():
        print(f"  {version}: {r['invariant_flagged']} flagged / {r['benchmark_failed']} failed "
              f"| recall {r['recall_of_failures']} precision {r['precision_of_flags']}")
        for violation, count in r["violation_counts"].items():
            print(f"      {violation:44} {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
