"""Run the reproducible offline improvement pipeline in dependency order."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from improvement.evaluate import ROOT


def run(module: str, *args: str) -> None:
    command = [sys.executable, "-m", module, *args]
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sync-live", action="store_true", help="Refresh the frozen selection from Sarvam before scoring.")
    parser.add_argument("--skip-optimize", action="store_true")
    parser.add_argument("--skip-track", action="store_true")
    args = parser.parse_args()
    if args.sync_live:
        run("improvement.ingest")
    run("improvement.evaluate")
    run("improvement.mine_failures")
    if not args.skip_optimize:
        run("improvement.optimize")
    if not args.skip_track:
        run("improvement.track")
    run("improvement.export_dashboard")
    print("pipeline complete: baseline remains frozen; candidate voice impact is not claimed until the matched round")


if __name__ == "__main__":
    main()
