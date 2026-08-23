"""Compute a champion's regressions and the stuck bucket (holes: consolidation input, H3).

Two outputs, both plain JSON lists of scenario ids:

* ``regressions``: scenarios the parent passed and the champion fails. These are
  the consolidation phase's trainset — the systemic replacement for the human
  edit that repaired generation-zero's champion by hand. A protection sample of
  the champion's own new fixes is included so consolidation cannot trade them
  away silently.

* ``stuck``: scenarios that failed under both the baseline and the champion with
  the same missing-write signature. Prompt search has had two distinct texts and
  every reflection's attention available, and the failure did not move — the
  working hypothesis is that it is not reachable from prompt space (model
  capability, channel limits). They are excluded from the *next* generation's
  search attention but never from its verdicts: scoring stays honest, the search
  just stops grinding on them. Each generation re-tests them, so a scenario that
  becomes winnable re-enters on the evidence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BULK = ROOT / "artifacts" / "campaign2" / "chat_bulk"


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


def signature(row: dict) -> str:
    return json.dumps(sorted(m.split("{")[0] for m in
                             row["grade"].get("missing_required_env",
                                              row["grade"]["missing_required"])))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent", required=True, help="verdict prefix, e.g. v3")
    parser.add_argument("--champion", required=True, help="verdict prefix, e.g. g1")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--protect", type=int, default=10,
                        help="how many of the champion's fixes to protect in consolidation")
    args = parser.parse_args()

    parent, champion = load(args.parent), load(args.champion)
    shared = sorted(set(parent) & set(champion))

    regressions = [s for s in shared if passed(parent[s]) and not passed(champion[s])]
    fixes = [s for s in shared if not passed(parent[s]) and passed(champion[s])]
    stuck = [s for s in shared
             if not passed(parent[s]) and not passed(champion[s])
             and signature(parent[s]) == signature(champion[s])]

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    consolidation = regressions + fixes[:args.protect]
    (out / "regressions.json").write_text(json.dumps(regressions, indent=1))
    (out / "consolidation_trainset.json").write_text(json.dumps(consolidation, indent=1))
    (out / "stuck.json").write_text(json.dumps(stuck, indent=1))

    print(f"  regressions {len(regressions)} | fixes {len(fixes)} "
          f"(protecting {min(args.protect, len(fixes))}) | stuck {len(stuck)}")
    for sid in regressions[:8]:
        print(f"    REGR {sid} {champion[sid]['family']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
