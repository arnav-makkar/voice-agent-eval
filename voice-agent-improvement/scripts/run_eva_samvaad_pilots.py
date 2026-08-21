"""Run the three predeclared EVA-Samvaad pilot records under a hard budget."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_eva_samvaad_live import EVA_ROOT, ROOT, _build_config, _run  # noqa: E402


PILOT_RECORD_IDS = ["EMI-HINGLISH-FIXED-001", "EMI-HINGLISH-FIXED-002", "EMI-HINGLISH-FIXED-003"]
MANIFEST = ROOT / "artifacts" / "framework" / "emi" / "eva_voice_suite_v3_hinglish_fixed" / "manifest.json"
OUTPUT_ROOT = ROOT / "artifacts" / "eva_pilots"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-version", type=int, required=True)
    parser.add_argument("--max-sessions", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm-live-pilots", action="store_true")
    args = parser.parse_args()
    if args.max_sessions < len(PILOT_RECORD_IDS):
        parser.error(f"three pilots require --max-sessions of at least {len(PILOT_RECORD_IDS)}")
    if not args.dry_run and not args.confirm_live_pilots:
        parser.error("live pilot execution requires --confirm-live-pilots")

    load_dotenv(ROOT / ".env", override=False)
    run_id = f"emi_eva_v{args.app_version}_pilots_{datetime.now():%Y%m%d_%H%M%S}"
    plan = {
        "schema_version": "eva-samvaad-pilot-plan.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "mode": "dry_run" if args.dry_run else "live_pilots",
        "run_id": run_id,
        "app_version": args.app_version,
        "record_ids": PILOT_RECORD_IDS,
        "language_policy": "normal Hinglish only",
        "requested_provider_sessions": {
            "elevenlabs": len(PILOT_RECORD_IDS),
            "samvaad": len(PILOT_RECORD_IDS),
        },
        "max_sessions": args.max_sessions,
        "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
    }
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    run_dir = OUTPUT_ROOT / run_id
    if not args.dry_run:
        if run_dir.exists():
            raise RuntimeError(f"refusing to reuse run directory: {run_dir}")
        run_dir.mkdir(parents=True)
        (run_dir / "pilot_plan.json").write_text(
            json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    os.chdir(EVA_ROOT)
    config = _build_config(
        run_id=run_id,
        dry_run=args.dry_run,
        record_ids=PILOT_RECORD_IDS,
        num_trials=1,
        app_version=args.app_version,
        output_root=OUTPUT_ROOT,
        max_concurrent_conversations=1,
    )
    return asyncio.run(_run(config))


if __name__ == "__main__":
    raise SystemExit(main())
