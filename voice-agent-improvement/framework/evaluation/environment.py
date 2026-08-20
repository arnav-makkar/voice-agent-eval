"""Isolated EMI state and deterministic tools for execution-truth evaluation."""

from __future__ import annotations

import copy
import datetime as dt
from dataclasses import dataclass
from typing import Any


ALLOWED_DISPOSITIONS = {
    "payment_ready", "ptp_today", "fptp", "callback", "dispute",
    "already_paid", "wrong_number", "alternate_number", "rtp",
    "acknowledged", "escalation", "call_disconnected",
}


class ToolExecutionError(ValueError):
    pass


@dataclass
class EMIEnvironment:
    """Fresh per-scenario state. No state is shared across runs."""

    state: dict[str, Any]

    @classmethod
    def from_initial(cls, initial: dict[str, Any]) -> "EMIEnvironment":
        return cls(copy.deepcopy(initial))

    def snapshot(self) -> dict[str, Any]:
        return copy.deepcopy(self.state)

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "check_payment_status":
            return {
                "payment_status": self.state.get("payment_status", "unpaid"),
                "outstanding_amount": self.state.get("outstanding_amount"),
                "last_payment_reference": self.state.get("last_payment_reference"),
            }
        if name == "record_promise_to_pay":
            date = str(arguments.get("date", "")).strip()
            if not date:
                raise ToolExecutionError("date is required")
            try:
                parsed = dt.datetime.strptime(date, "%d-%m-%Y").date()
            except ValueError as exc:
                raise ToolExecutionError("date must be DD-MM-YYYY") from exc
            current = dt.datetime.strptime(str(self.state["current_date"]), "%d-%m-%Y").date()
            if parsed < current:
                raise ToolExecutionError("promise date cannot be in the past")
            self.state["promise_to_pay_date"] = date
            self.state["disposition"] = "ptp_today" if parsed == current else "fptp"
            return {"recorded": True, "date": date, "disposition": self.state["disposition"]}
        if name == "schedule_callback":
            date = str(arguments.get("date", "")).strip()
            window = str(arguments.get("time_window", "")).strip()
            if not date or not window:
                raise ToolExecutionError("date and time_window are required")
            try:
                dt.datetime.strptime(date, "%d-%m-%Y")
            except ValueError as exc:
                raise ToolExecutionError("callback date must be DD-MM-YYYY") from exc
            self.state["callback"] = {"date": date, "time_window": window}
            self.state["disposition"] = "callback"
            return {"scheduled": True, **self.state["callback"]}
        if name == "record_disposition":
            disposition = str(arguments.get("disposition", "")).strip()
            if disposition not in ALLOWED_DISPOSITIONS:
                raise ToolExecutionError(f"invalid disposition: {disposition}")
            self.state["disposition"] = disposition
            return {"recorded": True, "disposition": disposition}
        raise ToolExecutionError(f"unknown tool: {name}")


def dotted_get(record: dict[str, Any], path: str) -> Any:
    value: Any = record
    for key in path.split("."):
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value

