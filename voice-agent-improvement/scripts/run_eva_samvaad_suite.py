"""Run the frozen matched EVA–Samvaad voice suite under an explicit budget.

This wrapper never deploys an Indus version.  It runs only the exact version
supplied by ``--app-version`` and refuses to start when the requested number of
provider sessions exceeds ``--max-sessions``.
"""

from __future__ import annotations

import argparse
import asyncio
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


MANIFEST = ROOT / "artifacts" / "framework" / "emi" / "eva_voice_suite_v1" / "manifest.json"
OUTPUT_ROOT = ROOT / "artifacts" / "eva_matched_live"


def _record_ids(suite: str) -> list[str]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return [row["record_id"] for row in manifest["records"] if suite == "all" or row["suite"] == suite]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-version", type=int, required=True)
    parser.add_argument("--suite", choices=("core", "acoustic", "all"), default="core")
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--max-sessions", type=int, required=True)
    parser.add_argument("--max-concurrent", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm-live-suite", action="store_true")
    args = parser.parse_args()
    if args.trials < 1:
        parser.error("--trials must be at least 1")
    if args.max_concurrent < 1:
        parser.error("--max-concurrent must be at least 1")
    if not args.dry_run and not args.confirm_live_suite:
        parser.error("live suite execution requires --confirm-live-suite")

    load_dotenv(ROOT / ".env", override=False)
    ids = _record_ids(args.suite)
    requested_sessions = len(ids) * args.trials
    if requested_sessions > args.max_sessions:
        parser.error(
            f"requested {requested_sessions} ElevenLabs + {requested_sessions} Samvaad sessions; "
            f"increase --max-sessions from {args.max_sessions} explicitly"
        )
    run_id = f"emi_eva_v{args.app_version}_{args.suite}_{datetime.now():%Y%m%d_%H%M%S}"
    run_dir = OUTPUT_ROOT / run_id
    if run_dir.exists():
        raise RuntimeError(f"refusing to reuse run directory: {run_dir}")

    plan = {
        "schema_version": "eva-samvaad-suite-plan.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "mode": "dry_run" if args.dry_run else "live_matched_suite",
        "run_id": run_id,
        "app_version": args.app_version,
        "suite": args.suite,
        "record_ids": ids,
        "trials": args.trials,
        "requested_provider_sessions": {"elevenlabs": requested_sessions, "samvaad": requested_sessions},
        "max_sessions": args.max_sessions,
        "max_concurrent": args.max_concurrent,
        "manifest_sha256": __import__("hashlib").sha256(MANIFEST.read_bytes()).hexdigest(),
    }
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    if args.dry_run:
        # Config construction validates credentials and EVA shapes but the
        # upstream dry-run opens no provider conversation.
        config = _build_config(
            run_id=run_id,
            dry_run=True,
            record_ids=ids,
            num_trials=args.trials,
            app_version=args.app_version,
            output_root=OUTPUT_ROOT,
            max_concurrent_conversations=args.max_concurrent,
        )
        os.chdir(EVA_ROOT)
        return asyncio.run(_run(config))

    run_dir.mkdir(parents=True)
    (run_dir / "suite_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chdir(EVA_ROOT)
    config = _build_config(
        run_id=run_id,
        dry_run=False,
        record_ids=ids,
        num_trials=args.trials,
        app_version=args.app_version,
        output_root=OUTPUT_ROOT,
        max_concurrent_conversations=args.max_concurrent,
    )
    return asyncio.run(_run(config))


if __name__ == "__main__":
    raise SystemExit(main())
