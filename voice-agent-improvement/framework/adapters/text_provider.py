"""Provider selection for the text tier's system under test.

The agent being measured runs on whichever model the campaign pins. Gemini is
the default; a Sarvam text-to-text key drops in as a configuration change rather
than a rewrite, because both are reached through the same structured-output
contract that `GeminiJsonClient` already defines.

The provider must not change between the BASE and IMPROVED passes of a
campaign — that would make the comparison measure two things at once. The
manifest records which provider produced each result so the pin is auditable.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import requests

from framework.adapters.gemini import GeminiJsonClient, GeminiResult


SARVAM_CHAT_URL = "https://api.sarvam.ai/v1/chat/completions"
DEFAULT_SARVAM_MODEL = "sarvam-m"


class TextProvider(Protocol):
    """What the runner needs from a system under test."""

    model: str

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        response_schema: dict[str, Any],
        temperature: float = 0.2,
        thinking_level: str = "high",
        cache_namespace: str = "default",
        use_cache: bool = True,
    ) -> GeminiResult: ...


@dataclass
class SarvamJsonClient:
    """Sarvam chat-completions behind the same contract as the Gemini client.

    Sarvam's endpoint is OpenAI-compatible, so structured output is requested
    through the schema in the system turn and validated on return rather than
    enforced by the API.
    """

    model: str = DEFAULT_SARVAM_MODEL
    api_key: str = ""
    timeout_seconds: float = 120
    max_retries: int = 3

    def __post_init__(self) -> None:
        self.api_key = self.api_key or os.environ.get("SARVAM_API_KEY", "")
        if not self.api_key:
            raise RuntimeError(
                "SARVAM_API_KEY is not set. The Voice Agents key does not "
                "authorise the text API — it returns 403 invalid_api_key_error."
            )

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        response_schema: dict[str, Any],
        temperature: float = 0.2,
        thinking_level: str = "high",
        cache_namespace: str = "default",
        use_cache: bool = True,
    ) -> GeminiResult:
        instruction = (
            f"{system}\n\nReturn ONLY a JSON object matching this schema, with no "
            f"prose and no code fence:\n{json.dumps(response_schema)}"
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": instruction},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
        }
        last: Exception | None = None
        for _ in range(self.max_retries):
            try:
                response = requests.post(
                    SARVAM_CHAT_URL,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "api-subscription-key": self.api_key,
                    },
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                body = response.json()
                text = body["choices"][0]["message"]["content"].strip()
                if text.startswith("```"):
                    text = text.split("```")[1].removeprefix("json").strip()
                return GeminiResult(
                    data=json.loads(text),
                    metadata={
                        "provider": "sarvam",
                        "model": body.get("model", self.model),
                        "usage": body.get("usage"),
                    },
                )
            except Exception as exc:  # noqa: BLE001 - retried, then surfaced
                last = exc
        raise RuntimeError(f"Sarvam text request failed after {self.max_retries} attempts: {last}")


def build_text_provider(
    *,
    provider: str | None = None,
    model: str | None = None,
    cache_dir: Path | None = None,
) -> TextProvider:
    """Return the pinned system under test.

    `provider` defaults to `LOOPLINE_TEXT_PROVIDER`, then to Gemini.
    """
    choice = (provider or os.environ.get("LOOPLINE_TEXT_PROVIDER") or "gemini").lower()
    if choice == "sarvam":
        return SarvamJsonClient(model=model or DEFAULT_SARVAM_MODEL)
    if choice == "gemini":
        return GeminiJsonClient(model=model or "gemini-3.6-flash", cache_dir=cache_dir)
    raise ValueError(f"unknown text provider: {choice!r}")


def describe_provider(client: TextProvider) -> dict[str, str]:
    """Provenance for the manifest, so a result can name what produced it."""
    return {
        "provider": "sarvam" if isinstance(client, SarvamJsonClient) else "gemini",
        "model": client.model,
    }
