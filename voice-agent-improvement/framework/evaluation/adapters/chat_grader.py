"""Grade one text-chat conversation against its frozen scenario contract.

Extracted from the suite runner so the optimiser, the regrade tool and the
runner all share one implementation — two graders that drift apart is how a
campaign ends up arguing with itself about what passed.

Environment-conditioned dates (grader v1.1)
-------------------------------------------
The text-chat channel binds the variables *stored on the agent* and ignores
per-request values, so the agent always believes today is the stored
``currentDate`` even though each scenario carries its own. A scenario that pins
``date == its own currentDate`` (the caller said "aaj") is then unwinnable
strictly: the agent resolves "today" correctly and still writes a different day.

v1.1 therefore accepts, for a pinned date equal to the scenario's currentDate or
tomorrowDate, the *stored environment's* value of that same relation. This is
not a relaxation of behaviour — the relation the agent had to compute is
unchanged — it is correcting the expected value to the environment the agent was
actually given. Anything else pinned (an absolute date the caller spoke, a
disposition, a trigger) must still match exactly. Both strict and v1.1 verdicts
are returned so reports can always show the stricter number beside it.
"""

from __future__ import annotations

from typing import Any

# The environment's clock, read from the live agent — never hardcoded.
#
# A constant here is a silent time bomb: it was one, for exactly one day. The
# stored currentDate went stale overnight, the agent resolved "kal" correctly
# against the real calendar, and this grader compared it against yesterday's,
# scoring callback_capture 2/12 when the true figure was 11/11. A whole ladder
# had to be re-measured.
#
# So the values are fetched once per process from the same authoring API that
# sets them, and cached. If the agent is unreachable the grader refuses to guess
# — an unknown clock disables date conditioning rather than inventing one, which
# makes a date-pinned scenario fail loudly instead of passing for the wrong
# reason. Callers that want a specific clock pass env_dates explicitly.

DATE_RELATIONS = ("currentDate", "tomorrowDate", "nearFutureDate", "cutoffDate")

_ENV_DATES_CACHE: dict[str, str] | None = None


def live_env_dates() -> dict[str, str]:
    """The clock currently in force on the deployed agent."""
    global _ENV_DATES_CACHE
    if _ENV_DATES_CACHE is None:
        try:
            from framework.evaluation.adapters import indus_authoring
            live = indus_authoring.stored_agent_variables()
            _ENV_DATES_CACHE = {
                key: live[key]
                for key in DATE_RELATIONS
                if key in live
            }
        except Exception:
            _ENV_DATES_CACHE = {}
    return _ENV_DATES_CACHE


def _action_satisfied(
    events: list[dict], name: str, want: dict, scenario_ctx: dict, env_dates: dict
) -> tuple[bool, bool]:
    """(strict, env_conditioned) satisfaction for one required action."""
    strict = env = False
    for event in events:
        if event.get("tool") != name:
            continue
        args = event.get("arguments") or event.get("body") or {}
        ok_strict = all(str(args.get(k, "")) == str(v) for k, v in want.items())
        ok_env = True
        for key, value in want.items():
            got = str(args.get(key, ""))
            if got == str(value):
                continue
            if key == "date":
                # The scenario pins an absolute date, but the channel never
                # delivers the scenario's clock to the agent — it only ever sees
                # the environment's. So a pinned date that *is* one of the
                # scenario's own clock variables is really a relation ("today",
                # "tomorrow"), and the agent satisfies it by producing the
                # environment's value for that same relation. Anything else the
                # caller named outright must still match exactly.
                relation = next(
                    (rel for rel in DATE_RELATIONS
                     if str(scenario_ctx.get(rel, "")) == str(value)),
                    None,
                )
                if relation and got == env_dates.get(relation):
                    continue
            ok_env = False
            break
        strict = strict or ok_strict
        env = env or ok_env
        if strict and env:
            break
    return strict, env


def grade(
    scenario: dict,
    events: list[dict],
    state: dict,
    env_dates: dict[str, str] | None = None,
) -> dict[str, Any]:
    env_dates = env_dates if env_dates is not None else live_env_dates()
    ctx = scenario.get("visible_context") or {}
    fired = [e.get("tool") for e in events]

    missing_strict: list[str] = []
    missing_env: list[str] = []
    for action in scenario.get("required_actions") or []:
        name = action["name"]
        want = action.get("arguments") or {}
        strict, env = _action_satisfied(events, name, want, ctx, env_dates)
        label = name + (f"{want}" if want else "")
        if not strict:
            missing_strict.append(label)
        if not env:
            missing_env.append(label)

    accepted = scenario.get("accepted_dispositions") or []
    disposition = state.get("disposition")
    disposition_ok = (not accepted) or (disposition in accepted)

    return {
        "tools_fired": fired,
        "missing_required": missing_strict,
        "missing_required_env": missing_env,
        "disposition": disposition,
        "disposition_ok": disposition_ok,
        "passed": not missing_strict and disposition_ok,
        "passed_env": not missing_env and disposition_ok,
    }
