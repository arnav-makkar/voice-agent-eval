"""The clock must never be hardcoded, and a stale one must fail loudly.

This regression test exists because a stale `currentDate` silently scored a
correct agent as broken for a whole overnight run — callback_capture read 2/12
when it was 11/11 — and the cause was a date literal in the grader.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from framework.evaluation.adapters import chat_grader  # noqa: E402
from framework.evaluation.adapters.indus_authoring import _derive_dates  # noqa: E402

SCENARIO = {
    "visible_context": {"currentDate": "01-01-2030", "tomorrowDate": "02-01-2030"},
    "required_actions": [{"name": "schedule_callback", "arguments": {"date": "02-01-2030"}}],
    "accepted_dispositions": ["callback"],
}


def _events(booked: str):
    return [{"tool": "schedule_callback", "arguments": {"date": booked}}]


def test_agent_matching_the_environments_tomorrow_passes():
    """The scenario says "tomorrow"; the agent can only see the env's clock."""
    env = {"currentDate": "23-08-2026", "tomorrowDate": "24-08-2026"}
    result = chat_grader.grade(SCENARIO, _events("24-08-2026"),
                               {"disposition": "callback"}, env_dates=env)
    assert result["passed_env"], result
    assert not result["passed"], "strict grading must still require the literal date"


def test_a_date_from_neither_clock_still_fails():
    env = {"currentDate": "23-08-2026", "tomorrowDate": "24-08-2026"}
    result = chat_grader.grade(SCENARIO, _events("30-08-2026"),
                               {"disposition": "callback"}, env_dates=env)
    assert not result["passed_env"], "an unrelated date must not be credited"


def test_grader_holds_no_hardcoded_dates():
    """A literal date in this module is the exact bug this test guards."""
    import re
    source = (ROOT / "framework/evaluation/adapters/chat_grader.py").read_text()
    code = "\n".join(
        line for line in source.splitlines()
        if not line.strip().startswith("#")
    )
    body = code.split('"""', 2)[-1]          # drop the module docstring
    assert not re.search(r"\d{2}-\d{2}-\d{4}", body), (
        "chat_grader must not contain a date literal — read the clock from the "
        "live agent instead"
    )


def test_derived_dates_follow_the_real_calendar():
    today = date(2026, 8, 23)
    derived = _derive_dates(today)
    assert derived["currentDate"] == "23-08-2026"
    assert derived["tomorrowDate"] == (today + timedelta(days=1)).strftime("%d-%m-%Y")
    assert derived["nearFutureDate"] == (today + timedelta(days=3)).strftime("%d-%m-%Y")
