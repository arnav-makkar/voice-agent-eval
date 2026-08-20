"""Run the isolated Loopline EMI tool service used by Indus API tools."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from framework.tool_service import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8788)
    parser.add_argument("--db", type=Path, default=ROOT / "artifacts" / "tool_service" / "tools.db")
    parser.add_argument(
        "--allow-unauthenticated-tools",
        action="store_true",
        help=(
            "Allow only seeded synthetic tool-effect endpoints without transport auth. "
            "Evaluation use only; run seeding/readback stay authenticated."
        ),
    )
    args = parser.parse_args()
    load_dotenv(ROOT / ".env", override=False)
    secret = os.getenv("LOOPLINE_TOOL_SECRET", "")
    if not secret:
        raise SystemExit("Set LOOPLINE_TOOL_SECRET in .env before starting the service")
    uvicorn.run(
        create_app(
            db_path=args.db,
            secret=secret,
            allow_unauthenticated_tools=args.allow_unauthenticated_tools,
        ),
        host=args.host,
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
