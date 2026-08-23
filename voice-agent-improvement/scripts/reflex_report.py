"""The generation ladder, with the statistics that make it defensible.

Three additions over a raw pass-rate table:

* **McNemar's exact test** on paired flips. 180 scenarios ran under both
  versions, so the honest question is not "is 129 > 98" but "are 29 fixes
  against 6 breaks explainable by coin-flips on discordant pairs". The exact
  binomial answer is reported per rung.
* **Wilson intervals** on the blind rate, so a small-n gate says its own
  uncertainty out loud.
* **The noise probe's sigma**: any delta below 2·sigma is labelled within-noise,
  whatever its sign — the same rule for gains as for losses.

Also reports a quality guard (mean agent words per turn) so a task-completion
gain bought with verbose robotic turns is visible immediately.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BULK = ROOT / "artifacts" / "campaign2" / "chat_bulk"
IMP = ROOT / "artifacts" / "campaign2" / "improvement"

GUARDRAIL_FAMILIES = {"credential_guardrail", "wrong_party_privacy",
                      "channel_unavailable", "conditional_promise_trap",
                      "safety_escalation", "fraud_escalation"}


def load(prefix: str) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for path in sorted(BULK.glob(f"{prefix}_*.jsonl")):
        for line in path.read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                rows[row["scenario_id"]] = row
    return rows


def passed(row: dict) -> bool:
    return row["grade"].get("passed_env", row["grade"]["passed"])


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact binomial on discordant pairs (b fixes, c breaks)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def wilson(p_hat: float, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    denom = 1 + z * z / n
    centre = (p_hat + z * z / (2 * n)) / denom
    half = z * math.sqrt(p_hat * (1 - p_hat) / n + z * z / (4 * n * n)) / denom
    return (round(centre - half, 3), round(centre + half, 3))


def words_per_agent_turn(rows: dict[str, dict]) -> float:
    total_words = total_turns = 0
    for row in rows.values():
        for line in row["transcript"].splitlines():
            if line.startswith("agent: ") and line[7:].strip():
                total_words += len(line[7:].split())
                total_turns += 1
    return round(total_words / total_turns, 1) if total_turns else 0.0


def rung(parent: dict, champ: dict, blind_splits: set[str], sigma60: float) -> dict:
    shared = sorted(set(parent) & set(champ))
    fixes = sum(1 for s in shared if not passed(parent[s]) and passed(champ[s]))
    breaks = sum(1 for s in shared if passed(parent[s]) and not passed(champ[s]))
    blind = [s for s in shared if parent[s]["split"] in blind_splits]
    guard = [s for s in shared if parent[s]["family"] in GUARDRAIL_FAMILIES]

    def rate(rows, ids):
        return sum(1 for s in ids if passed(rows[s])), len(ids)

    bp, bn = rate(parent, blind)
    bc, _ = rate(champ, blind)
    gp, gn = rate(parent, guard)
    gc, _ = rate(champ, guard)
    op, on = rate(parent, shared)
    oc, _ = rate(champ, shared)
    delta_blind = bc - bp
    return {
        "n": on, "overall": {"parent": op, "champion": oc},
        "blind": {"n": bn, "parent": bp, "champion": bc,
                  "champion_ci": wilson(bc / bn if bn else 0, bn),
                  "within_noise": abs(delta_blind) < 2 * sigma60},
        "guardrails": {"n": gn, "parent": gp, "champion": gc,
                       "veto": gc < gp},
        "paired": {"fixed": fixes, "broken": breaks,
                   "mcnemar_p": round(mcnemar_exact(fixes, breaks), 5)},
        "quality_words_per_turn": {"parent": words_per_agent_turn(parent),
                                   "champion": words_per_agent_turn(champ)},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rungs", nargs="+", default=["v3:g1", "g1:g2", "v3:g2"],
                        help="parent:champion verdict prefixes")
    parser.add_argument("--out", default=str(IMP / "reflex_ladder.json"))
    args = parser.parse_args()

    sigma60 = 0.0
    probe_path = IMP / "noise_probe.json"
    if probe_path.exists():
        sigma60 = json.loads(probe_path.read_text())["sigma_pass_count"].get("60", 0.0)

    report = {"sigma60": sigma60, "rungs": {}}
    for spec in args.rungs:
        parent_prefix, champ_prefix = spec.split(":")
        parent, champ = load(parent_prefix), load(champ_prefix)
        if not parent or not champ:
            report["rungs"][spec] = "not run"
            continue
        blind_splits = {"validation", "regression"}
        if any(r["split"] == "blind_g2" for r in champ.values()):
            blind_splits |= {"blind_g2"}
        report["rungs"][spec] = rung(parent, champ, blind_splits, sigma60)

    Path(args.out).write_text(json.dumps(report, indent=2))
    for spec, r in report["rungs"].items():
        if isinstance(r, str):
            print(f"  {spec}: {r}")
            continue
        b = r["blind"]
        print(f"  {spec}: overall {r['overall']['parent']}→{r['overall']['champion']}/{r['n']} | "
              f"blind {b['parent']}→{b['champion']}/{b['n']} CI{b['champion_ci']} "
              f"{'NOISE' if b['within_noise'] else 'signal'} | "
              f"±{r['paired']['fixed']}/-{r['paired']['broken']} p={r['paired']['mcnemar_p']} | "
              f"guard {r['guardrails']['parent']}→{r['guardrails']['champion']}"
              f"{' VETO' if r['guardrails']['veto'] else ''} | "
              f"words/turn {r['quality_words_per_turn']['parent']}→"
              f"{r['quality_words_per_turn']['champion']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
