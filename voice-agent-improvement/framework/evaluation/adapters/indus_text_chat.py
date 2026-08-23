"""Drive the deployed Indus agent over its text-chat channel.

The Samvaad *SDK* chat is enterprise-gated — its signed-URL endpoint returns 404
for ``interaction_type=chat`` on this app — which is why the S2 pilot had to be
driven through the browser test console. The console itself, however, talks to a
plain REST channel:

    POST /api/app-runtime/channels/text-chat/orgs/{org}/workspaces/{ws}
         /apps/{app}/text-chat?app_version={n}

so the same substrate is reachable headlessly with a dashboard bearer token. That
matters for the bulk tier: 180 conversations driven through a DOM are slow,
fragile and impossible to parallelise, whereas this is an ordinary HTTP client.

Two properties are deliberate and must not be relaxed:

* ``app_version`` is explicit on every request. The console defaults to the open
  draft; a baseline that silently measured the draft instead of the committed
  version would be worthless.
* Tool truth is never read from ``debug_logs``. The logs are useful for tracing
  what the runtime *attempted*, but the graded record of what actually happened
  comes from the append-only journal, exactly as it does for voice and phone.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

import httpx

BASE = "https://apps.sarvam.ai/api/app-runtime/channels/text-chat"
ORG = "019fe148-1997-7cc7-bb7a-8029929d4008"
WORKSPACE = "019fe148-199b-787e-b8d7-b0c2d4e6acda"
APP = "EasyCredit--4e112b0d-9931"


def load_token(path: str = ".env.local") -> str:
    """Read the dashboard JWT.

    Kept out of ``.env`` and out of git: it is a short-lived session token for a
    human account, not a service credential, and it must never reach the repo.
    """
    token = os.getenv("SARVAM_DASH_JWT", "").strip()
    if token:
        return token
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("SARVAM_DASH_JWT="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("SARVAM_DASH_JWT not found in environment or .env.local")


@dataclass
class ChatTurn:
    speaker: str
    text: str


@dataclass
class ChatSession:
    """One conversation with the deployed agent."""

    app_version: int
    variables: dict[str, str]
    token: str
    interaction_id: str | None = None
    turns: list[ChatTurn] = field(default_factory=list)
    debug: list[dict[str, Any]] = field(default_factory=list)
    client: httpx.Client | None = None

    def _url(self) -> str:
        return (
            f"{BASE}/orgs/{ORG}/workspaces/{WORKSPACE}/apps/{APP}"
            f"/text-chat?app_version={self.app_version}"
        )

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
        }
        client = self.client or httpx
        response = client.post(self._url(), json=payload, headers=headers, timeout=120.0)
        if response.status_code != 200:
            raise RuntimeError(f"HTTP {response.status_code}: {response.text[:300]}")
        body = response.json()
        for entry in body.get("debug_logs") or []:
            self.debug.append(entry)
        return body

    def start(self, opening: str) -> str:
        """Open the interaction with the caller's first line.

        The channel rejects an empty ``text`` even on the opening request, so the
        conversation cannot be started and then spoken into: the caller's first
        turn *is* the start call. The agent's scripted greeting is delivered by
        the runtime rather than returned here, so only the reply is recorded.
        """
        self.turns.append(ChatTurn("caller", opening))
        body = self._post(
            {
                "stream": False,
                "text": opening,
                "start_interaction": True,
                "debug": True,
                "agent_variables": self.variables,
            }
        )
        self.interaction_id = body.get("interaction_id")
        reply = (body.get("text") or "").strip()
        self.turns.append(ChatTurn("agent", reply))
        return reply

    def say(self, text: str) -> str:
        """Send one caller turn and return the agent's reply."""
        if not self.interaction_id:
            raise RuntimeError("start() must be called before say()")
        self.turns.append(ChatTurn("caller", text))
        body = self._post(
            {
                "stream": False,
                "text": text,
                "start_interaction": False,
                "debug": True,
                "interaction_id": self.interaction_id,
            }
        )
        reply = (body.get("text") or "").strip()
        self.turns.append(ChatTurn("agent", reply))
        return reply

    def attempted_tools(self) -> list[str]:
        """Tool names the runtime *attempted*, for tracing only.

        Never use this to satisfy a required action: a tool the runtime tried and
        that failed, or that wrote to a different run, would count as success. The
        journal is the only record that decides that.
        """
        names: list[str] = []
        for entry in self.debug:
            blob = json.dumps(entry, ensure_ascii=False)
            for tool in (
                "check_payment_status",
                "record_promise_to_pay",
                "schedule_callback",
                "record_dispute",
                "escalate_to_human",
                "record_call_outcome",
            ):
                if tool in blob and tool not in names:
                    names.append(tool)
        return names

    def transcript(self) -> str:
        return "\n".join(f"{t.speaker}: {t.text}" for t in self.turns)
