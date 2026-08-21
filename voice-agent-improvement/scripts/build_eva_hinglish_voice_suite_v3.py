"""Build the corrected Hinglish-only EVA voice suite after the v19 pilot audit.

The v2 suite is immutable evidence of a failed pilot. It accidentally carried
relative dates from a 17-Aug fixture into a 19-Aug execution. This v3 suite
keeps the same source scenarios and ordering, but rebases relative date facts
before freezing new record IDs.
"""

from __future__ import annotations

import copy
import json

from build_eva_emi_voice_suite import EVA_DATA, EVA_SCENARIOS, ROOT, _load_sources, _record, _sha
from build_eva_hinglish_voice_suite import ACOUSTIC_CASES, CORE_SOURCE_IDS


MANIFEST = ROOT / "artifacts" / "framework" / "emi" / "eva_voice_suite_v3_hinglish_fixed" / "manifest.json"
PREFIX = "EMI-HINGLISH-FIXED-"
DATE_REBASE = {
    "17-08-2026": "19-08-2026",
    "18-08-2026": "20-08-2026",
    "17 August": "19 August",
    "18 August": "20 August",
}


def _rebase_relative_dates(source: dict) -> dict:
    row = copy.deepcopy(source)
    row["initial_environment"]["current_date"] = "19-08-2026"
    for action in row.get("required_actions", []):
        for key, value in list(action.get("arguments", {}).items()):
            if isinstance(value, str):
                action["arguments"][key] = DATE_REBASE.get(value, value)
    for step in row.get("user_steps", []):
        text = step.get("text", "")
        for old, new in DATE_REBASE.items():
            text = text.replace(old, new)
        step["text"] = text
    return row


def main() -> None:
    sources = _load_sources()
    selected = CORE_SOURCE_IDS + [source_id for source_id, _ in ACOUSTIC_CASES]
    non_hinglish = sorted({source_id for source_id in selected if sources[source_id]["language"] != "hinglish"})
    if non_hinglish:
        raise ValueError(f"active voice suite must be Hinglish-only: {non_hinglish}")

    existing = json.loads(EVA_DATA.read_text(encoding="utf-8"))
    existing = [row for row in existing if not row["id"].startswith(PREFIX)]
    records: list[dict] = []
    created: list[dict] = []

    def add(source_id: str, index: int, suite: str, acoustic: dict | None = None) -> None:
        record_id = f"{PREFIX}{index:03d}"
        source = _rebase_relative_dates(sources[source_id])
        record, scenario = _record(source, record_id, acoustic)
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
        "schema_version": "eva-emi-voice-suite.v3",
        "status": "frozen_after_v19_failure_before_next_live_execution",
        "language_policy": "ordinary Hindi-English code-switching only; reject non-Devanagari Indic scripts",
        "date_policy": "relative date facts rebased to the frozen 19-08-2026 fixture before record creation",
        "supersedes_for_future_runs": "eva_voice_suite_v2_hinglish",
        "preserves_failed_evidence": "emi_eva_v19_pilots_20260821_160827",
        "pilot_record_ids": [row["record_id"] for row in created[:3]],
        "records": created,
        "core_count": len(CORE_SOURCE_IDS),
        "acoustic_count": len(ACOUSTIC_CASES),
        "dataset_path": str(EVA_DATA),
        "dataset_sha256": _sha(EVA_DATA),
        "claim_boundary": (
            "Prospective corrected suite only. It has no live score. The v19 result remains a failed, invalid-for-"
            "promotion pilot and is never rewritten as an improvement."
        ),
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"dataset_sha256": manifest["dataset_sha256"], "records": len(records), "pilots": manifest["pilot_record_ids"]}, indent=2))


if __name__ == "__main__":
    main()
