"""Build the active 12-core + 6-acoustic Hinglish-only EVA voice suite.

The original multilingual suite remains frozen as ``eva_voice_suite_v1`` and
is never rewritten.  This v2 suite exists because the interview demo needs a
clean, comparable bot-to-bot story in the language used by the target agent:
ordinary Hindi/English code-switching (Hinglish), with no language-switch test
mixed into the three-call advance gate.
"""

from __future__ import annotations

import json

from build_eva_emi_voice_suite import (
    EVA_DATA,
    EVA_SCENARIOS,
    ROOT,
    _load_sources,
    _record,
    _sha,
)


MANIFEST = ROOT / "artifacts" / "framework" / "emi" / "eva_voice_suite_v2_hinglish" / "manifest.json"
PREFIX = "EMI-HINGLISH-VOICE-"

# The first three records are the pilot gate: direct pay-now, a future/today
# promise that must write state, and a callback that must write two arguments.
# Every source row is explicitly labelled Hinglish in the frozen scenario set.
CORE_SOURCE_IDS = [
    "EMI-DYN-001",
    "EMI-DYN-004",
    "EMI-DYN-020",
    "EMI-DYN-002",
    "EMI-DYN-006",
    "EMI-DYN-009",
    "EMI-DYN-010",
    "EMI-DYN-011",
    "EMI-DYN-015",
    "EMI-DYN-016",
    "EMI-DYN-017",
    "EMI-DYN-025",
]

ACOUSTIC_CASES = [
    ("EMI-DYN-001", {"kind": "background_noise", "snr_db": 12, "seed": 2301}),
    ("EMI-DYN-004", {"kind": "low_gain", "gain": 0.4, "seed": 2302}),
    ("EMI-DYN-020", {"kind": "packet_loss", "probability": 0.08, "seed": 2303}),
    ("EMI-DYN-015", {"kind": "jitter", "max_delay_ms": 80, "seed": 2304}),
    ("EMI-DYN-025", {"kind": "background_noise", "snr_db": 15, "seed": 2305}),
    ("EMI-DYN-030", {"kind": "low_gain", "gain": 0.55, "seed": 2306}),
]


def main() -> None:
    sources = _load_sources()
    selected = CORE_SOURCE_IDS + [source_id for source_id, _ in ACOUSTIC_CASES]
    non_hinglish = sorted({source_id for source_id in selected if sources[source_id]["language"] != "hinglish"})
    if non_hinglish:
        raise ValueError(f"active voice suite must be Hinglish-only: {non_hinglish}")

    existing = json.loads(EVA_DATA.read_text(encoding="utf-8"))
    existing = [row for row in existing if not row["id"].startswith(PREFIX)]
    records = []
    created = []

    def add(source_id: str, index: int, suite: str, acoustic: dict | None = None) -> None:
        record_id = f"{PREFIX}{index:03d}"
        record, scenario = _record(sources[source_id], record_id, acoustic)
        records.append(record)
        path = EVA_SCENARIOS / f"{record_id}.json"
        path.write_text(json.dumps(scenario, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        created.append(
            {
                "record_id": record_id,
                "source_id": source_id,
                "language": "hinglish",
                "suite": suite,
                "perturbation": acoustic,
                "scenario_path": str(path),
            }
        )

    for index, source_id in enumerate(CORE_SOURCE_IDS, 1):
        add(source_id, index, "core")
    for index, (source_id, acoustic) in enumerate(ACOUSTIC_CASES, len(CORE_SOURCE_IDS) + 1):
        add(source_id, index, "acoustic", acoustic)

    EVA_DATA.write_text(json.dumps(existing + records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "eva-emi-voice-suite.v2",
        "status": "frozen_before_hinglish_matched_live_execution",
        "language_policy": "normal Hinglish only; no Punjabi language-switch records",
        "pilot_record_ids": [row["record_id"] for row in created[:3]],
        "records": created,
        "core_count": len(CORE_SOURCE_IDS),
        "acoustic_count": len(ACOUSTIC_CASES),
        "dataset_path": str(EVA_DATA),
        "dataset_sha256": _sha(EVA_DATA),
        "claim_boundary": (
            "Prospective Hinglish-only matched live suite. The multilingual v1 suite and its historical pilots remain "
            "immutable. No improvement result exists until the same v2 record IDs run on baseline and candidate."
        ),
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"dataset_sha256": manifest["dataset_sha256"], "records": len(records), "pilots": manifest["pilot_record_ids"]}, indent=2))


if __name__ == "__main__":
    main()
