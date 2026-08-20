"""Revalidate and fully score a recovered run without opening voice sessions.

This may call configured judge models, but it never creates a new ElevenLabs
or Samvaad conversation.  The exact EVA-A/EVA-X component list comes from the
versioned live runner configuration.
"""

from __future__ import annotations

import argparse
import asyncio
import os

from dotenv import load_dotenv

from run_eva_samvaad_live import EVA_ROOT, ROOT, _build_config, _run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env", override=False)
    os.chdir(EVA_ROOT)
    config = _build_config(run_id=args.run_id, dry_run=False)
    config.max_rerun_attempts = 0
    config.force_revalidation = True
    config.force_rerun_metrics = True
    config.preflight = False
    return asyncio.run(_run(config))


if __name__ == "__main__":
    raise SystemExit(main())
