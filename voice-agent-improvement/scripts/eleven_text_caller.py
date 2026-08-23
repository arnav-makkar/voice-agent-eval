"""A text-mode ElevenLabs caller you can drive one turn at a time.

The voice path kept failing on turn-taking: at a 15 second turn timeout the
caller never got to speak, at 3 seconds it interrupted the agent 31 times in a
single call, and every attempt cost credits to discover. Text removes the timing
problem entirely — turns are explicit, nothing is inferred from silence — so the
conversation logic can be proven before any audio is involved.

The same ElevenLabs agent, persona and prompt are used, so what is validated here
carries over when the voice path is switched back on.

    from eleven_text_caller import TextCaller
    with TextCaller(prompt) as caller:
        first = caller.opening()
        reply = caller.say("नमस्ते, क्या मैं Arnav जी से बात कर रहा हूँ?")
"""

from __future__ import annotations

import os
import queue
import ssl
from pathlib import Path

import certifi
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation, ConversationInitiationData

ROOT = Path(__file__).resolve().parents[1]


def load_env(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


class _Silent:
    """The SDK expects an audio interface; text mode needs it to do nothing."""

    def start(self, *_a, **_k) -> None: ...
    def stop(self) -> None: ...
    def output(self, *_a, **_k) -> None: ...
    def interrupt(self) -> None: ...


class TextCaller:
    def __init__(self, prompt: str, *, agent_id: str | None = None, timeout: float = 45.0) -> None:
        load_env()
        os.environ.setdefault("SSL_CERT_FILE", certifi.where())
        self.agent_id = agent_id or os.environ["EVA_EN_USER_M"]
        self.timeout = timeout
        self._turns: queue.Queue[str] = queue.Queue()
        self._parts: list[str] = []
        self.transcript: list[dict[str, str]] = []
        self._conv = Conversation(
            client=ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"]),
            agent_id=self.agent_id,
            requires_auth=True,
            audio_interface=_Silent(),
            config=ConversationInitiationData(dynamic_variables={"prompt": prompt}),
            callback_agent_response=self._turns.put,
            # In text mode the full-response callback may never fire; the agent's
            # words arrive as chat parts instead. Collect both and de-duplicate.
            callback_agent_chat_response_part=self._parts.append,
        )

    def __enter__(self) -> "TextCaller":
        self._conv.start_session()
        return self

    def __exit__(self, *_exc) -> None:
        try:
            self._conv.end_session()
        except Exception:
            pass

    def _next(self) -> str:
        """Wait for the caller's next turn, joining any split responses."""
        import time

        parts: list[str] = []
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            try:
                parts.append(self._turns.get(timeout=1.0))
                break
            except queue.Empty:
                if self._parts:
                    time.sleep(1.5)          # let the streamed parts finish
                    parts.append("".join(self._parts))
                    self._parts.clear()
                    break
        if not parts:
            raise TimeoutError("caller produced no turn")
        while True:                          # drain anything that follows
            try:
                parts.append(self._turns.get(timeout=1.5))
            except queue.Empty:
                break
        text = " ".join(p.strip() for p in parts if p and p.strip())
        self.transcript.append({"role": "caller", "text": text})
        return text

    def opening(self) -> str:
        """The caller's first line, spoken before the agent says anything."""
        return self._next()

    def say(self, agent_text: str) -> str:
        """Give the caller what the agent just said; get its reply."""
        self.transcript.append({"role": "agent", "text": agent_text})
        self._conv.send_user_message(agent_text)
        return self._next()
