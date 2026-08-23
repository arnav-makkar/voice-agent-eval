"""Measure run-to-run variance of the evaluation itself (hole H1).

Every improvement claim rides on a denominator that was measured once. The
agent is stochastic, so the same prompt on the same scenarios does not score
identically twice — and until the size of that wobble is measured, a small
delta between two versions is indistinguishable from luck.

This runs the *current draft* twice over a stratified probe (4 scenarios per
family), with identical harness settings, and reports:

* the test–retest flip rate: fraction of scenarios whose verdict changed
  between two identical runs — the per-scenario noise probability;
* the implied standard deviation of a pass *count* on n scenarios
  (sigma ≈ sqrt(n · p_flip / 2), treating flips as symmetric);
* the concrete honesty rule the gate then applies: a blind delta smaller than
  2·sigma(60) is reported as "within noise", whatever its sign.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.gepa_optimize import SCENARIOS, run_scenario  # noqa: E402

OUT = ROOT / "artifacts" / "campaign2" / "improvement" / "noise_probe.json"


def probe_set(per_family: int = 3) -> list[str]:
    by_family: dict[str, list[str]] = {}
    for sid, scenario in sorted(SCENARIOS.items()):
        if scenario["split"] == "development":
            by_family.setdefault(scenario["failure_family"], []).append(sid)
    picked: list[str] = []
    for family in sorted(by_family):
        picked += by_family[family][:per_family]
    return picked


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-family", type=int, default=3)
    args = parser.parse_args()

    ids = probe_set(args.per_family)
    print(f"probe: {len(ids)} scenarios × 2 runs = {2*len(ids)} conversations")

    runs: list[dict[str, bool]] = []
    for run_index in (1, 2):
        verdicts: dict[str, bool] = {}
        for count, sid in enumerate(ids, 1):
            result, _, error = run_scenario(SCENARIOS[sid])
            verdicts[sid] = bool(result["passed_env"]) and not error
            print(f"  run{run_index} [{count}/{len(ids)}] {sid} "
                  f"{'ok' if verdicts[sid] else 'FAIL'}", flush=True)
        runs.append(verdicts)

    flips = [sid for sid in ids if runs[0][sid] != runs[1][sid]]
    p_flip = len(flips) / len(ids)
    sigma = {n: round(math.sqrt(n * p_flip / 2), 2) for n in (30, 60, 180)}

    report = {
        "n_scenarios": len(ids),
        "pass_run1": sum(runs[0].values()),
        "pass_run2": sum(runs[1].values()),
        "flipped": flips,
        "flip_rate": round(p_flip, 4),
        "sigma_pass_count": sigma,
        "gate_rule": f"a blind-60 delta below {round(2*sigma[60],1)} passes is reported as within noise",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
