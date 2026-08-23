"""Read and write the Indus draft agent's system prompt over the authoring API.

The dashboard editor saves through ``PUT /api/app-authoring/.../apps/{app_id}``
with the full app config wrapped in ``{"app": ...}``; the prompt itself lives at
``llm_config.agent_config.states.start.instructions``. This is what makes a
closed optimisation loop possible at all: candidates can be applied headlessly
in seconds instead of through a DOM editor.

Two invariants this module owns:

* The stored text escapes ``*``, ``\``` and ``_`` with backslashes (the editor's
  canonical form). Candidates are authored in plain text and converted here, so
  the optimiser never has to know about the escaping.
* Every write re-reads the config first and changes only the instructions field.
  The config carries tool wiring, variables and channel settings; a stale local
  copy PUT back whole could silently revert something the owner changed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from framework.evaluation.adapters.indus_text_chat import (  # noqa: E402
    APP,
    ORG,
    WORKSPACE,
    load_token,
)

BASE = f"https://apps.sarvam.ai/api/app-authoring/orgs/{ORG}/workspaces/{WORKSPACE}/apps"


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def escape(plain: str) -> str:
    return plain.replace("*", r"\*").replace("`", r"\`").replace("_", r"\_")


def unescape(stored: str) -> str:
    return stored.replace(r"\*", "*").replace(r"\`", "`").replace(r"\_", "_")


def get_config(token: str | None = None) -> dict:
    token = token or load_token()
    response = httpx.get(f"{BASE}/{APP}", headers=_headers(token), timeout=60)
    response.raise_for_status()
    return response.json()


def read_instructions(token: str | None = None) -> str:
    config = get_config(token)
    return unescape(config["llm_config"]["agent_config"]["states"]["start"]["instructions"])


def write_instructions(plain_text: str, token: str | None = None) -> dict:
    """Apply a new system prompt to the draft. Returns {'status', 'chars'}."""
    token = token or load_token()
    config = get_config(token)
    config["llm_config"]["agent_config"]["states"]["start"]["instructions"] = escape(plain_text)
    response = httpx.put(
        f"{BASE}/{APP}",
        json={"app": config, "app_name": APP},
        headers=_headers(token),
        timeout=120,
    )
    response.raise_for_status()
    return {"status": response.status_code, "chars": len(plain_text)}


def stored_agent_variables(token: str | None = None) -> dict:
    """The variable values the runtime actually binds (per-request ones are ignored)."""
    config = get_config(token)
    raw = config["llm_config"]["agent_config"].get("agent_variables") or {}
    if isinstance(raw, dict):
        out = {}
        for key, value in raw.items():
            out[key] = value.get("value") if isinstance(value, dict) else value
        return out
    return {}

# ── Clock hygiene ───────────────────────────────────────────────────────────
# The agent's notion of "today" is an injected variable, and a stale one silently
# corrupts every measurement that involves a relative date. It cost this campaign
# a full re-run: the stored currentDate went one day stale overnight, the agent
# resolved "kal" correctly against the real calendar, and the grader compared it
# against yesterday's — scoring callback_capture 2/12 when it was 11/11.
#
# The rule that prevents a repeat: the environment's clock is set from the real
# clock at the start of every run, and the grader reads the same values back from
# the live agent rather than from a constant. Nothing hardcodes a date.

DATE_FORMAT = "%d-%m-%Y"


def _derive_dates(today: "date") -> dict[str, str]:
    from datetime import timedelta
    return {
        "currentDate": today.strftime(DATE_FORMAT),
        "tomorrowDate": (today + timedelta(days=1)).strftime(DATE_FORMAT),
        "nearFutureDate": (today + timedelta(days=3)).strftime(DATE_FORMAT),
        "cutoffDate": (today + timedelta(days=5)).strftime(DATE_FORMAT),
    }


def set_agent_variables(values: dict[str, str], token: str | None = None) -> dict[str, str]:
    """Write agent variables server-side, and verify they took.

    The deployed agent resolves ``{{campaignId}}`` and friends from these stored
    values, not from anything passed per request — a variable sent alongside a
    text-chat turn is silently ignored. Since ``campaignId`` is the key the agent
    writes its journal under, every run that wants its own ledger has to set it
    here first, and wait for the write to land before dialling.

    Only declared variables are written; unknown keys raise rather than being
    dropped, so a typo cannot quietly send a call to the previous run's ledger.
    """
    token = token or load_token()
    config = get_config(token)
    variables = config["llm_config"]["agent_config"].get("agent_variables") or {}

    unknown = [k for k in values if k not in variables]
    if unknown:
        raise KeyError(f"agent does not declare these variables: {unknown}")

    for key, value in values.items():
        entry = variables[key]
        if isinstance(entry, dict):
            entry["value"] = str(value)
        else:
            variables[key] = str(value)

    response = httpx.put(
        f"{BASE}/{APP}",
        json={"app": config, "app_name": APP},
        headers=_headers(token),
        timeout=120,
    )
    response.raise_for_status()

    live = stored_agent_variables(token)
    for key, value in values.items():
        if live.get(key) != str(value):
            raise RuntimeError(
                f"variable write did not take: {key} is {live.get(key)!r}, "
                f"expected {str(value)!r}"
            )
    return {k: live[k] for k in values}


def sync_env_dates(token: str | None = None, today: "date | None" = None) -> dict[str, str]:
    """Set the agent's clock variables from the real calendar. Idempotent.

    Only variables the agent actually declares are written, so this stays correct
    if the variable set changes. Returns the values now in force, which is what a
    grader should be conditioned on.
    """
    from datetime import date as _date
    token = token or load_token()
    wanted = _derive_dates(today or _date.today())

    config = get_config(token)
    variables = config["llm_config"]["agent_config"].get("agent_variables") or {}
    changed = {}
    for key, value in wanted.items():
        entry = variables.get(key)
        if entry is None:
            continue
        current = entry.get("value") if isinstance(entry, dict) else entry
        if str(current) != value:
            changed[key] = (current, value)
        if isinstance(entry, dict):
            entry["value"] = value
        else:
            variables[key] = value

    if changed:
        response = httpx.put(
            f"{BASE}/{APP}",
            json={"app": config, "app_name": APP},
            headers=_headers(token),
            timeout=120,
        )
        response.raise_for_status()

    live = stored_agent_variables(token)
    in_force = {k: live[k] for k in wanted if k in live}
    for key, value in wanted.items():
        if key in live and live[key] != value:
            raise RuntimeError(
                f"clock sync failed: {key} is {live[key]!r}, expected {value!r}"
            )
    return in_force


def assert_clock_fresh(token: str | None = None) -> dict[str, str]:
    """Fail loudly if the agent's clock is not today's. Cheap; call before a run."""
    from datetime import date as _date
    wanted = _derive_dates(_date.today())
    live = stored_agent_variables(token)
    stale = {k: (live.get(k), v) for k, v in wanted.items()
             if k in live and live[k] != v}
    if stale:
        raise RuntimeError(
            "agent clock is stale — run sync_env_dates() first: "
            + ", ".join(f"{k} is {a} but today implies {b}" for k, (a, b) in stale.items())
        )
    return {k: live[k] for k in wanted if k in live}
