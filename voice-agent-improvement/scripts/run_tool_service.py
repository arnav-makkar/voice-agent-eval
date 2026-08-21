"""Run the isolated Loopline EMI tool service used by Indus API tools.

Request journalling lives here rather than in ``framework/tool_service.py``
because that module is part of the frozen evaluator bundle.  Proving that the
deployed platform reached the service is an observability concern, not an
evaluation-semantics change, so it is added by the launcher and the frozen
component stays byte-identical to its recorded hash.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from framework.tool_service import create_app


def attach_request_journal(app: FastAPI, journal_path: Path) -> FastAPI:
    """Record every inbound request, including ones that fail.

    A request that never arrives and a request that arrives and is rejected look
    identical from the caller's side, and the platform's own tool tester reports
    both as ambiguous. Journalling every request — with the status, the client,
    and whether a credential was presented — makes the difference decisive.
    The credential value itself is never written.
    """
    journal_path.parent.mkdir(parents=True, exist_ok=True)

    @app.middleware("http")
    async def _journal(request: Request, call_next: Any) -> Any:
        body = await request.body()

        async def replay() -> dict[str, Any]:
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = replay  # noqa: SLF001 - re-arm the stream after reading it
        response = await call_next(request)
        try:
            payload = json.loads(body) if body else None
        except json.JSONDecodeError:
            payload = {"unparsed_bytes": len(body)}
        with journal_path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "at": datetime.now(UTC).isoformat(),
                        "method": request.method,
                        "path": request.url.path,
                        "status": response.status_code,
                        "credential_presented": bool(request.headers.get("x-loopline-tool-key")),
                        "user_agent": request.headers.get("user-agent"),
                        "client_host": request.client.host if request.client else None,
                        "body": payload,
                    },
                    sort_keys=True,
                )
                + "\n"
            )
        return response

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8788)
    parser.add_argument("--db", type=Path, default=ROOT / "artifacts" / "tool_service" / "tools.db")
    parser.add_argument(
        "--journal",
        type=Path,
        default=ROOT / "artifacts" / "tool_service" / "inbound_requests.jsonl",
        help="Append every inbound request here, including rejected ones.",
    )
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
    app = create_app(
        db_path=args.db,
        secret=secret,
        allow_unauthenticated_tools=args.allow_unauthenticated_tools,
    )
    uvicorn.run(
        attach_request_journal(app, args.journal),
        host=args.host,
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
