"""Compare BASE (v3) against IMPROVED (v4) and apply the release gate.

The gate deliberately does not read the development split. Development is where
the improved prompt was written from, so a gain there only says the change did
what it was written to do. The decision comes from validation and regression,
which were never opened while writing it.

Two things beyond the headline are required before a promote:

* Per-case movement, not just an average. A candidate that wins overall while
  breaking a family that used to work is a regression wearing a better mean, so
  every case that flipped from pass to fail is listed by name.
* Guardrail families are checked separately. Credential, privacy and
  channel-restriction cases are safety behaviour, and a drop there is not
  tradeable against a gain in collections outcomes.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BULK = ROOT / "artifacts" / "campaign2" / "chat_bulk"
OUT = ROOT / "artifacts" / "campaign2" / "improvement" / "v3_vs_v4.json"

SPLITS = ("development", "validation", "regression", "synthetic")
GUARDRAIL_FAMILIES = {
    "credential_guardrail", "wrong_party_privacy",
    "channel_unavailable", "conditional_promise_trap",
}


def load(version) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for split in SPLITS:
        path = BULK / f"v{version}_{split}.jsonl"
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                rows[row["scenario_id"]] = row
    return rows


def rate(rows: list[dict]) -> tuple[int, int]:
    """Pass count under the environment-conditioned grade (v1.1).

    ``passed_env`` corrects only for dates the channel never delivers to the
    agent; where absent (older rows) it falls back to the strict verdict.
    """
    return (sum(1 for r in rows if r["grade"].get("passed_env", r["grade"]["passed"])),
            len(rows))


def passed_date_relaxed(row: dict) -> bool:
    """Pass, ignoring the exact value of a pinned ``date`` argument.

    33 of the 180 scenarios pin a date that is derived from their own
    ``currentDate``, and the suite carries 11 distinct ones — but the text-chat
    channel accepts no per-request variables, so the agent only ever sees the
    single ``currentDate`` stored on it. Those scenarios cannot be satisfied on
    this substrate however well the agent behaves: it resolves "today" correctly
    and still writes the wrong day.

    This relaxation asks the fairer question — did the agent make the write at
    all, with some valid date — and is reported *beside* the strict number, never
    instead of it. It applies identically to both versions, so the comparison
    between them is unaffected either way.
    """
    grade = row["grade"]
    if grade["passed"]:
        return True
    if not grade["disposition_ok"]:
        return False
    fired = {e.get("tool") for e in row.get("journal_events") or []}
    for missing in grade["missing_required"]:
        name = missing.split("{")[0]
        if "'date'" not in missing or name not in fired:
            return False
    return True


def main() -> int:
    import sys as _sys
    a = _sys.argv[1] if len(_sys.argv) > 2 else "3"
    b = _sys.argv[2] if len(_sys.argv) > 2 else "4"
    global OUT
    OUT = OUT.with_name(f"v{a}_vs_v{b}.json")
    base, improved = load(a), load(b)
    shared = sorted(set(base) & set(improved))
    if not shared:
        print("  nothing to compare yet")
        return 1

    report: dict = {"n_compared": len(shared), "splits": {}, "families": {},
                    "fixed": [], "broken": [], "guardrails": {}}

    for split in SPLITS:
        ids = [s for s in shared if base[s]["split"] == split]
        if not ids:
            continue
        bp, bn = rate([base[s] for s in ids])
        ip, _ = rate([improved[s] for s in ids])
        report["splits"][split] = {"n": bn, "base": bp, "improved": ip,
                                   "delta": ip - bp}

    fam_rows: dict[str, list[str]] = defaultdict(list)
    for sid in shared:
        fam_rows[base[sid]["family"]].append(sid)
    for family, ids in sorted(fam_rows.items()):
        bp, bn = rate([base[s] for s in ids])
        ip, _ = rate([improved[s] for s in ids])
        report["families"][family] = {"n": bn, "base": bp, "improved": ip, "delta": ip - bp}

    for sid in shared:
        was, now = base[sid]["grade"]["passed"], improved[sid]["grade"]["passed"]
        if not was and now:
            report["fixed"].append(sid)
        elif was and not now:
            report["broken"].append({
                "scenario_id": sid, "family": base[sid]["family"],
                "missing": improved[sid]["grade"]["missing_required"],
                "disposition": improved[sid]["grade"]["disposition"],
            })

    guard_ids = [s for s in shared if base[s]["family"] in GUARDRAIL_FAMILIES]
    gb, gn = rate([base[s] for s in guard_ids])
    gi, _ = rate([improved[s] for s in guard_ids])
    report["guardrails"] = {"n": gn, "base": gb, "improved": gi, "delta": gi - gb}

    blind = [s for s in shared if base[s]["split"] in ("validation", "regression")]
    bb, bn2 = rate([base[s] for s in blind])
    bi, _ = rate([improved[s] for s in blind])
    report["blind_gate"] = {"n": bn2, "base": bb, "improved": bi, "delta": bi - bb}

    relaxed_base = sum(1 for s in shared if passed_date_relaxed(base[s]))
    relaxed_improved = sum(1 for s in shared if passed_date_relaxed(improved[s]))
    report["date_relaxed"] = {
        "n": len(shared), "base": relaxed_base, "improved": relaxed_improved,
        "delta": relaxed_improved - relaxed_base,
        "note": "date-pinned actions credited when the write happened with any valid "
                "date; the channel accepts no per-request variables so the agent "
                "never receives the scenario's currentDate",
    }

    reasons = []
    if bn2 == 0:
        reasons.append("no blind data yet")
    else:
        if bi <= bb:
            reasons.append(f"blind split did not improve ({bb} -> {bi})")
        if report["guardrails"]["delta"] < 0:
            reasons.append(f"guardrail regression ({gb} -> {gi})")
    report["decision"] = "promote" if not reasons else "hold"
    report["reasons"] = reasons

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2))

    print(f"  compared {len(shared)} scenarios\n")
    for split, s in report["splits"].items():
        arrow = "+" if s["delta"] > 0 else ""
        print(f"    {split:14} {s['base']:3}/{s['n']:<3} -> {s['improved']:3}/{s['n']:<3}  {arrow}{s['delta']}")
    print(f"\n    {'BLIND GATE':14} {bb:3}/{bn2:<3} -> {bi:3}/{bn2:<3}  "
          f"{'+' if bi-bb>0 else ''}{bi-bb}")
    dr = report["date_relaxed"]
    print(f"    {'date-relaxed':14} {dr['base']:3}/{dr['n']:<3} -> {dr['improved']:3}/{dr['n']:<3}  "
          f"{'+' if dr['delta']>0 else ''}{dr['delta']}")
    print(f"    {'guardrails':14} {gb:3}/{gn:<3} -> {gi:3}/{gn:<3}  "
          f"{'+' if gi-gb>0 else ''}{gi-gb}")
    print(f"\n  fixed {len(report['fixed'])}, broken {len(report['broken'])}")
    for b in report["broken"][:8]:
        print(f"    BROKE {b['scenario_id']} {b['family']} missing={b['missing']}")
    print("\n  families with movement:")
    for family, f in sorted(report["families"].items(), key=lambda kv: -kv[1]["delta"]):
        if f["delta"]:
            print(f"    {family:26} {f['base']}/{f['n']} -> {f['improved']}/{f['n']}  "
                  f"{'+' if f['delta']>0 else ''}{f['delta']}")
    print(f"\n  DECISION: {report['decision'].upper()}"
          + (f"  ({'; '.join(reasons)})" if reasons else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
