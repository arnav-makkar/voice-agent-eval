"""Scenario-isolated EMI tool service for live Indus evaluation.

The service is intentionally small and deterministic.  Every tool request is
scoped to a pre-seeded ``run_id`` and ``account_id``; no call can see or mutate
another trial's state.  The append-only event table is the execution-truth
source used by the release gate and dashboard.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field, field_validator


DATE_PATTERN = r"^\d{2}-\d{2}-\d{4}$"


class SeedRun(BaseModel):
    run_id: str = Field(min_length=3, max_length=160)
    account_id: str = Field(min_length=3, max_length=160)
    outstanding_amount: str = Field(pattern=r"^\d+(?:\.\d{1,2})?$")
    payment_status: Literal["unpaid", "paid", "pending"] = "unpaid"


class ToolContext(BaseModel):
    run_id: str = Field(min_length=3, max_length=160)
    account_id: str = Field(min_length=3, max_length=160)
    event_id: str | None = Field(default=None, max_length=160)


class PromiseRequest(ToolContext):
    date: str = Field(pattern=DATE_PATTERN)

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        datetime.strptime(value, "%d-%m-%Y")
        return value


class CallbackRequest(ToolContext):
    date: str = Field(pattern=DATE_PATTERN)
    time_window: str = Field(min_length=3, max_length=80)

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        datetime.strptime(value, "%d-%m-%Y")
        return value


class DisputeRequest(ToolContext):
    """A dispute the caller raised, recorded verbatim rather than adjudicated."""

    reason: str = Field(min_length=3, max_length=300)


class EscalationRequest(ToolContext):
    """Hand the call to a human. The trigger is recorded, never inferred."""

    trigger: Literal["fraud_allegation", "customer_distress", "abuse", "legal_threat", "other"]
    note: str = Field(min_length=3, max_length=300)


class CallOutcomeRequest(ToolContext):
    disposition: Literal[
        "payment_ready",
        "ptp_today",
        "fptp",
        "callback",
        "dispute",
        "already_paid",
        "wrong_number",
        "alternate_number",
        "rtp",
        "acknowledged",
        "escalation",
        "call_disconnected",
    ]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


class ToolStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _init(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    initial_state_json TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE,
                    run_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    arguments_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );
                """
            )

    def seed(self, request: SeedRun) -> dict[str, Any]:
        state = {
            "account_id": request.account_id,
            "payment_status": request.payment_status,
            "outstanding_amount": request.outstanding_amount,
            "promise_to_pay_date": None,
            "callback": None,
            "disposition": None,
            "dispute_reason": None,
            "escalation": None,
        }
        now = _utc_now()
        with self.connect() as connection:
            try:
                connection.execute(
                    "INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?)",
                    (request.run_id, request.account_id, json.dumps(state), json.dumps(state), now, now),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError(f"run_id already exists: {request.run_id}") from exc
        return self.read(request.run_id)

    def read(self, run_id: str) -> dict[str, Any]:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            if row is None:
                raise KeyError(run_id)
            events = connection.execute(
                "SELECT sequence, event_id, tool_name, arguments_json, result_json, created_at "
                "FROM events WHERE run_id = ? ORDER BY sequence",
                (run_id,),
            ).fetchall()
        return {
            "run_id": row["run_id"],
            "account_id": row["account_id"],
            "initial_state": json.loads(row["initial_state_json"]),
            "state": json.loads(row["state_json"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "events": [
                {
                    "sequence": event["sequence"],
                    "event_id": event["event_id"],
                    "tool_name": event["tool_name"],
                    "arguments": json.loads(event["arguments_json"]),
                    "result": json.loads(event["result_json"]),
                    "created_at": event["created_at"],
                }
                for event in events
            ],
        }

    def execute(
        self,
        *,
        context: ToolContext,
        tool_name: str,
        arguments: dict[str, Any],
        mutate: Any,
    ) -> dict[str, Any]:
        now = _utc_now()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if context.event_id:
                existing = connection.execute(
                    "SELECT result_json FROM events WHERE event_id = ?", (context.event_id,)
                ).fetchone()
                if existing is not None:
                    return json.loads(existing["result_json"])
            row = connection.execute("SELECT * FROM runs WHERE run_id = ?", (context.run_id,)).fetchone()
            if row is None:
                raise KeyError(context.run_id)
            if row["account_id"] != context.account_id:
                raise PermissionError("account_id does not match seeded run")
            state = json.loads(row["state_json"])
            result = mutate(state)
            connection.execute(
                "UPDATE runs SET state_json = ?, updated_at = ? WHERE run_id = ?",
                (json.dumps(state), now, context.run_id),
            )
            connection.execute(
                "INSERT INTO events(event_id, run_id, tool_name, arguments_json, result_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    context.event_id,
                    context.run_id,
                    tool_name,
                    json.dumps(arguments),
                    json.dumps(result),
                    now,
                ),
            )
        return result


def create_app(
    *,
    db_path: Path | None = None,
    secret: str | None = None,
    allow_unauthenticated_tools: bool = False,
) -> FastAPI:
    resolved_path = db_path or Path(
        os.getenv("AGENT_TOOL_DB")
        or os.getenv("LOOPLINE_TOOL_DB", "artifacts/tool_service/tools.db"))
    # AGENT_TOOL_SECRET is the current name; the LOOPLINE_* names are accepted as
    # fallbacks because the deployed platform's tool definitions still send the
    # original header, and breaking the live wire contract during a rename would
    # reproduce the exact silent-transport failure this service exists to expose.
    resolved_secret = secret or os.getenv("AGENT_TOOL_SECRET") or os.getenv("LOOPLINE_TOOL_SECRET", "")
    if not resolved_secret:
        raise RuntimeError("AGENT_TOOL_SECRET is required")
    store = ToolStore(resolved_path)
    app = FastAPI(title="EMI evaluation tools", version="1.0.0")

    def authorize(
        x_agent_tool_key: Annotated[str | None, Header()] = None,
        x_loopline_tool_key: Annotated[str | None, Header()] = None,
    ) -> None:
        if resolved_secret not in (x_agent_tool_key, x_loopline_tool_key):
            raise HTTPException(status_code=401, detail="invalid tool credential")

    def authorize_tool(
        x_agent_tool_key: Annotated[str | None, Header()] = None,
        x_loopline_tool_key: Annotated[str | None, Header()] = None,
    ) -> None:
        """Authorize tool effects, with an explicit synthetic-evaluation escape hatch.

        The bypass is deliberately limited to the three tool-effect endpoints. Run
        seeding and state inspection always require the configured secret, and the
        store still rejects unknown run IDs and account mismatches. Production code
        must leave ``allow_unauthenticated_tools`` at its fail-closed default.
        """
        if allow_unauthenticated_tools:
            return
        authorize(x_agent_tool_key, x_loopline_tool_key)

    def run_or_404(run_id: str) -> dict[str, Any]:
        try:
            return store.read(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="unknown run_id") from exc

    def execute_or_error(**kwargs: Any) -> dict[str, Any]:
        try:
            return store.execute(**kwargs)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="unknown run_id") from exc
        except PermissionError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/evaluation/runs", dependencies=[Depends(authorize)])
    def seed_run(request: SeedRun) -> dict[str, Any]:
        try:
            return store.seed(request)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/v1/evaluation/runs/{run_id}", dependencies=[Depends(authorize)])
    def get_run(run_id: str) -> dict[str, Any]:
        return run_or_404(run_id)

    @app.post("/v1/tools/check-payment-status", dependencies=[Depends(authorize_tool)])
    def check_payment_status(request: ToolContext) -> dict[str, Any]:
        def read_status(state: dict[str, Any]) -> dict[str, Any]:
            return {
                "payment_status": state["payment_status"],
                "outstanding_amount": state["outstanding_amount"],
            }

        return execute_or_error(
            context=request,
            tool_name="check_payment_status",
            arguments=request.model_dump(),
            mutate=read_status,
        )

    @app.post("/v1/tools/record-promise-to-pay", dependencies=[Depends(authorize_tool)])
    def record_promise_to_pay(request: PromiseRequest) -> dict[str, Any]:
        def record(state: dict[str, Any]) -> dict[str, Any]:
            state["promise_to_pay_date"] = request.date
            state["disposition"] = "fptp"
            return {"recorded": True, "date": request.date, "disposition": "fptp"}

        return execute_or_error(
            context=request,
            tool_name="record_promise_to_pay",
            arguments=request.model_dump(),
            mutate=record,
        )

    @app.post("/v1/tools/record-dispute", dependencies=[Depends(authorize_tool)])
    def record_dispute(request: DisputeRequest) -> dict[str, Any]:
        def record(state: dict[str, Any]) -> dict[str, Any]:
            state["dispute_reason"] = request.reason
            state["disposition"] = "dispute"
            return {"recorded": True, "reason": request.reason, "disposition": "dispute"}

        return execute_or_error(
            context=request,
            tool_name="record_dispute",
            arguments=request.model_dump(),
            mutate=record,
        )

    @app.post("/v1/tools/escalate-to-human", dependencies=[Depends(authorize_tool)])
    def escalate_to_human(request: EscalationRequest) -> dict[str, Any]:
        def record(state: dict[str, Any]) -> dict[str, Any]:
            state["escalation"] = {"trigger": request.trigger, "note": request.note}
            state["disposition"] = "escalation"
            return {"recorded": True, "trigger": request.trigger, "disposition": "escalation"}

        return execute_or_error(
            context=request,
            tool_name="escalate_to_human",
            arguments=request.model_dump(),
            mutate=record,
        )

    @app.post("/v1/tools/schedule-callback", dependencies=[Depends(authorize_tool)])
    def schedule_callback(request: CallbackRequest) -> dict[str, Any]:
        def record(state: dict[str, Any]) -> dict[str, Any]:
            state["callback"] = {"date": request.date, "time_window": request.time_window}
            state["disposition"] = "callback"
            return {"scheduled": True, "date": request.date, "time_window": request.time_window}

        return execute_or_error(
            context=request,
            tool_name="schedule_callback",
            arguments=request.model_dump(),
            mutate=record,
        )

    @app.post("/v1/tools/record-call-outcome", dependencies=[Depends(authorize_tool)])
    def record_call_outcome(request: CallOutcomeRequest) -> dict[str, Any]:
        def record(state: dict[str, Any]) -> dict[str, Any]:
            state["disposition"] = request.disposition
            return {"recorded": True, "disposition": request.disposition}

        return execute_or_error(
            context=request,
            tool_name="record_call_outcome",
            arguments=request.model_dump(),
            mutate=record,
        )

    app.state.tool_store = store
    return app
