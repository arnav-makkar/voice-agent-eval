"""Poll read-only Indus analytics and refresh local dashboard data.

This command is for future operational monitoring. The interview baseline is
selection-locked; unseen attempts are not silently added to that benchmark.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time

from improvement.evaluate import ROOT


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.interval < 10:
        parser.error("--interval must be at least 10 seconds")
    while True:
        subprocess.run(
            [sys.executable, "-m", "improvement.sync_monitoring"],
            cwd=ROOT,
            check=True,
        )
        subprocess.run([sys.executable, "-m", "improvement.export_dashboard"], cwd=ROOT, check=True)
        if args.once:
            return
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
