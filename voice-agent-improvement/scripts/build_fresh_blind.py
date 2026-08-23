"""Generate a fresh blind set from the same frozen generator, deduplicated.

Hole H2: a blind set reused across generations stops being blind — each gate
leaks a little selection pressure into it. The fix is fresh scenarios per
generation, from the same distribution, that no search phase has ever seen.

The generator is deterministic and combinatorial, so widening variants_per_cell
re-deals the whole universe: same families, same utterance banks, same persona
and perturbation rotation, different combinations. Everything in that wider
universe whose content hash does not collide with the frozen 165 (or the
synthetic 15) is a genuinely unseen scenario drawn by the same process. This
script extracts a stratified 60 of them, splits them blind_g1_reserve /
blind_g2, and records their hashes in a manifest before anything runs — the
sets exist, hashed, prior to any candidate they will judge.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
BENCH = ROOT / "artifacts" / "framework" / "emi" / "benchmark_v1"

import framework.datasets.build_benchmark as generator  # noqa: E402


def content_key(scenario: dict) -> str:
    """Identity = what the conversation would actually be, not the id."""
    steps = [s["text"] if isinstance(s, dict) else str(s) for s in scenario["user_steps"]]
    basis = json.dumps({
        "family": scenario["failure_family"],
        "language": scenario["language"],
        "steps": steps,
        "persona": scenario.get("persona"),
        "required": scenario.get("required_actions"),
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(basis.encode()).hexdigest()


def main() -> int:
    existing: set[str] = set()
    for name in ("development", "validation", "regression", "synthetic"):
        for line in (BENCH / f"{name}.jsonl").read_text().splitlines():
            if line.strip():
                existing.add(content_key(json.loads(line)))

    # build() writes its output files directly into its OUTPUT directory, so the
    # wide universe is generated into a sandbox — pointing it at the real
    # benchmark directory would overwrite the frozen suite (which happened once,
    # recovered only because the generator is deterministic).
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        real_output = generator.OUTPUT
        try:
            generator.OUTPUT = Path(tmp)
            generator.build(variants_per_cell=7, base_date="2026-08-22")
        finally:
            generator.OUTPUT = real_output
        pool = []
        for path in Path(tmp).glob("*.jsonl"):
            for line in path.read_text().splitlines():
                if not line.strip():
                    continue
                scenario = json.loads(line)
                key = content_key(scenario)
                if key not in existing:
                    scenario["_content_key"] = key
                    pool.append(scenario)

    by_family: dict[str, list[dict]] = defaultdict(list)
    for scenario in pool:
        by_family[scenario["failure_family"]].append(scenario)

    picked: list[dict] = []
    round_index = 0
    while len(picked) < 60:
        progressed = False
        for family in sorted(by_family):
            members = by_family[family]
            if round_index < len(members) and len(picked) < 60:
                picked.append(members[round_index])
                progressed = True
        if not progressed:
            break
        round_index += 1

    for index, scenario in enumerate(picked):
        scenario["scenario_id"] = f"EMI-BLIND-{index+1:04d}"
        scenario["split"] = "blind_g1_reserve" if index % 2 == 0 else "blind_g2"
        scenario["source_group"] = "fresh-blind-" + scenario["source_group"]

    for split in ("blind_g1_reserve", "blind_g2"):
        rows = [s for s in picked if s["split"] == split]
        path = BENCH / f"{split}.jsonl"
        path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        print(f"  {split}: {len(rows)} scenarios  sha256={digest[:16]}…")

    manifest = {
        "generated_from": "build_benchmark.build(variants_per_cell=7)",
        "deduplicated_against": "development+validation+regression+synthetic content keys",
        "pool_size_after_dedup": len(pool),
        "files": {
            split: hashlib.sha256((BENCH / f"{split}.jsonl").read_bytes()).hexdigest()
            for split in ("blind_g1_reserve", "blind_g2")
        },
    }
    (BENCH / "fresh_blind_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"  manifest written; pool had {len(pool)} unseen scenarios")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
