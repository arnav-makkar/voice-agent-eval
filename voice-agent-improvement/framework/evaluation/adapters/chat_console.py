"""Score Indus chat-console runs with the project's frozen evaluator.

The chat pilot is driven through the Indus test console, which is a browser
surface rather than an SDK, so its output arrives as a transcript plus the tool
ledger rather than as a ``ScenarioRun``. This adapter rebuilds the contract
object so console runs are graded by exactly the same evaluator as every other
tier — the alternative, a bespoke scorer for this tier, is how two tiers end up
disagreeing about what "passed" means.

Two properties are deliberate. Tool events come from the append-only journal,
never from the transcript, so a spoken claim can never satisfy a required
action. And the declared disposition is read from the ledger the tools wrote,
not from anything the agent said, so say-versus-do stays detectable.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from framework.evaluation.contracts import ConversationTurn, ScenarioRun, ToolEvent

SCHEMA_VERSION = "scenario-run.v3"
ADAPTER = "indus_chat_console.v1"

# Console chrome that is not part of the conversation.
_CHROME = re.compile(
    r"^(End Conversation|Collecting output variables…|Open in Analytics|Start New Chat|"
    r"OUTPUT VARIABLES|Call summary|Response|Params|Request completed successfully\.|"
    r"Detailed interaction information.*|\d+|-)$"
)


def parse_transcript(transcript: str, caller_steps: list[str]) -> list[ConversationTurn]:
    """Split the console text into actor-attributed turns.

    Caller turns are known exactly — the harness sent them — so they are matched
    verbatim and everything else that survives chrome filtering is the agent.
    """
    pending = list(caller_steps)
    turns: list[ConversationTurn] = []
    for raw in transcript.splitlines():
        line = raw.strip()
        if not line or _CHROME.match(line) or line.startswith("{") or line.startswith("}"):
            continue
        if line.startswith('"') and line.endswith(","):
            continue
        if pending and line == pending[0].strip():
            turns.append(ConversationTurn(len(turns) + 1, "caller", line))
            pending.pop(0)
            continue
        # A bare tool name printed by the console is an event marker, not speech.
        if re.fullmatch(r"[a-z_]{6,40}", line):
            continue
        turns.append(ConversationTurn(len(turns) + 1, "agent", line))
    return turns


def build_run(
    *,
    scenario_id: str,
    candidate_id: str,
    transcript: str,
    caller_steps: list[str],
    ledger: dict[str, Any],
    initial_state: dict[str, Any],
    started_at: str | None = None,
) -> ScenarioRun:
    events = [
        ToolEvent(
            sequence=index,
            name=item["tool"],
            arguments=item.get("arguments", {}),
            result={},
            status="success",
        )
        for index, item in enumerate(ledger.get("events", []), start=1)
    ]
    final_state = ledger.get("state") or {}
    turns = parse_transcript(transcript, caller_steps)
    now = started_at or datetime.now(UTC).isoformat()
    return ScenarioRun(
        schema_version=SCHEMA_VERSION,
        run_id=f"CHAT-{scenario_id}",
        scenario_id=scenario_id,
        candidate_id=candidate_id,
        candidate_hash="",
        adapter=ADAPTER,
        started_at=now,
        ended_at=now,
        # The console prints an "End Conversation" marker when the agent invokes
        # the built-in End Interaction tool. That is the only terminal signal the
        # surface exposes, so it maps to agent_terminal; a transcript without it
        # means the caller script ran out while the agent was still talking.
        termination_reason="agent_terminal" if "End Conversation" in transcript else "script_exhausted",
        interaction_id=None,
        turns=turns,
        tool_events=events,
        initial_state=initial_state,
        final_state=final_state,
        # Execution truth only: the outcome is whatever the tools actually wrote.
        agent_declared_disposition=str(final_state.get("disposition") or "call_disconnected"),
        simulator_validation={
            "passed": True,
            "caller_turns": sum(turn.actor == "caller" for turn in turns),
            "scripted_caller": True,
            "note": "Caller turns are fixed script text, so caller fidelity is exact by construction.",
        },
        provenance={"surface": "indus_chat_console", "tool_truth": "append_only_journal"},
    )
