"""Fail-closed budget and duplicate guards for paid live evaluation sessions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from framework.core.io import write_json


class LiveBudgetError(RuntimeError):
    """Raised before a provider session starts when a live guard fails."""


def _fingerprint(*, scenario_id: str, candidate_id: str, interaction_type: str) -> str:
    payload = json.dumps(
        {
            "scenario_id": scenario_id,
            "candidate_id": candidate_id,
            "interaction_type": interaction_type,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LiveReservation:
    reservation_id: str
    fingerprint: str
    scenario_id: str
    candidate_id: str
    interaction_type: str
    estimated_credits: float


class LiveBudgetLedger:
    """Durable reservations count connection attempts, including failures.

    Sarvam may charge a minimum unit once a live session connects. A retry is
    therefore a new paid experiment, not an invisible transport detail. Every
    attempt is reserved before ``agent.start()`` and remains in the ledger even
    when the provider times out.
    """

    schema_version = "live-budget-ledger.v1"

    def __init__(
        self,
        path: Path,
        *,
        max_sessions: int,
        credit_budget: float,
        estimated_credits_per_session: float = 4.5,
        confirmed_live: bool = False,
        allow_duplicate: bool = False,
    ) -> None:
        if max_sessions < 1:
            raise ValueError("max_sessions must be positive")
        if credit_budget <= 0 or estimated_credits_per_session <= 0:
            raise ValueError("credit amounts must be positive")
        self.path = path
        self.max_sessions = max_sessions
        self.credit_budget = float(credit_budget)
        self.estimated_credits_per_session = float(estimated_credits_per_session)
        self.confirmed_live = confirmed_live
        self.allow_duplicate = allow_duplicate

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {
                "schema_version": self.schema_version,
                "created_at": datetime.now(UTC).isoformat(),
                "max_sessions": self.max_sessions,
                "credit_budget": self.credit_budget,
                "estimated_credits_per_session": self.estimated_credits_per_session,
                "reservations": [],
            }
        record = json.loads(self.path.read_text(encoding="utf-8"))
        if record.get("schema_version") != self.schema_version:
            raise LiveBudgetError(f"unsupported live ledger: {record.get('schema_version')}")
        return record

    def reserve(self, *, scenario_id: str, candidate_id: str, interaction_type: str) -> LiveReservation:
        if not self.confirmed_live:
            raise LiveBudgetError("live provider call blocked; pass --confirm-live")
        ledger = self._load()
        reservations = list(ledger.get("reservations", []))
        fingerprint = _fingerprint(
            scenario_id=scenario_id,
            candidate_id=candidate_id,
            interaction_type=interaction_type,
        )
        if not self.allow_duplicate and any(item.get("fingerprint") == fingerprint for item in reservations):
            raise LiveBudgetError(
                f"duplicate live scenario blocked: {scenario_id} for {candidate_id}; "
                "pass --allow-duplicate only for a predeclared rerun"
            )
        if len(reservations) >= self.max_sessions:
            raise LiveBudgetError(f"live session cap reached: {len(reservations)}/{self.max_sessions}")
        spent = sum(float(item.get("estimated_credits", 0)) for item in reservations)
        projected = spent + self.estimated_credits_per_session
        if projected > self.credit_budget + 1e-9:
            raise LiveBudgetError(
                f"live credit budget exceeded: projected {projected:.2f} > {self.credit_budget:.2f}"
            )
        timestamp = datetime.now(UTC).isoformat()
        reservation = LiveReservation(
            reservation_id=f"LIVE-{len(reservations) + 1:04d}-{fingerprint[:10]}",
            fingerprint=fingerprint,
            scenario_id=scenario_id,
            candidate_id=candidate_id,
            interaction_type=interaction_type,
            estimated_credits=self.estimated_credits_per_session,
        )
        reservations.append(
            {
                **reservation.__dict__,
                "status": "reserved",
                "reserved_at": timestamp,
                "updated_at": timestamp,
            }
        )
        ledger.update(
            {
                "max_sessions": self.max_sessions,
                "credit_budget": self.credit_budget,
                "estimated_credits_per_session": self.estimated_credits_per_session,
                "estimated_credits_reserved": projected,
                "reservations": reservations,
            }
        )
        write_json(self.path, ledger)
        return reservation

    def finalize(
        self,
        reservation: LiveReservation,
        *,
        status: str,
        interaction_id: str | None = None,
        error: str | None = None,
    ) -> None:
        if status not in {"completed", "failed", "connected_empty", "cancelled_before_start"}:
            raise ValueError(f"unsupported live reservation status: {status}")
        ledger = self._load()
        matched = False
        for item in ledger.get("reservations", []):
            if item.get("reservation_id") == reservation.reservation_id:
                item.update(
                    {
                        "status": status,
                        "interaction_id": interaction_id,
                        "error": error,
                        "updated_at": datetime.now(UTC).isoformat(),
                    }
                )
                matched = True
                break
        if not matched:
            raise LiveBudgetError(f"reservation not found: {reservation.reservation_id}")
        write_json(self.path, ledger)

