"""Exact Instant Outbound request construction and transport."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import json
from typing import Any
from urllib import error, request

from .config import Settings


OUTBOUNDS_BASE_URL = "https://apps.sarvam.ai/api/outbounds"


class SarvamAPIError(RuntimeError):
    """A Voice Agents API request failed or returned an invalid response."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def build_outbound_payload(
    settings: Settings,
    *,
    agent_variables: Mapping[str, Any] | None = None,
    initial_bot_message: str | None = None,
    initial_state_name: str | None = None,
    webhook_url: str | None = None,
    webhook_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the payload emitted by Indus's Instant outbound recipe.

    Optional blocks are omitted unless their values are explicitly supplied.
    This keeps the first smoke test on the committed agent defaults.
    """

    app_config: dict[str, Any] = {
        "app_id": settings.app_id,
        "app_version": settings.app_version,
        "app_type": "agent",
        "connection_config": {
            "connection_id": settings.connection_id,
            "agent_phone_number": settings.agent_phone_number,
        },
    }

    if agent_variables:
        app_config["agent_variables"] = dict(agent_variables)

    overrides = {
        key: value
        for key, value in {
            "initial_bot_message": initial_bot_message,
            "initial_state_name": initial_state_name,
        }.items()
        if value
    }
    if overrides:
        app_config["app_overrides"] = overrides

    payload: dict[str, Any] = {
        "app_config": app_config,
        "user_config": {"user_phone_number": settings.user_phone_number},
    }

    if webhook_url:
        payload["webhook_config"] = {
            "url": webhook_url,
            "metadata": dict(webhook_metadata) if webhook_metadata else None,
        }

    return payload


class SarvamVoiceAgentsClient:
    def __init__(
        self,
        *,
        api_key: str,
        org_id: str,
        workspace_id: str,
        timeout_seconds: float = 30.0,
        opener: Callable[..., Any] = request.urlopen,
    ) -> None:
        if not api_key:
            raise ValueError("A Voice Agents API key is required")
        self.api_key = api_key
        self.org_id = org_id
        self.workspace_id = workspace_id
        self.timeout_seconds = timeout_seconds
        self._opener = opener

    @property
    def instant_outbound_url(self) -> str:
        return (
            f"{OUTBOUNDS_BASE_URL}/v1/orgs/{self.org_id}"
            f"/workspaces/{self.workspace_id}/outbounds"
        )

    def create_outbound_call(self, payload: Mapping[str, Any]) -> str:
        encoded_payload = json.dumps(payload).encode("utf-8")
        outbound_request = request.Request(
            self.instant_outbound_url,
            data=encoded_payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-API-Key": self.api_key,
            },
        )

        try:
            with self._opener(
                outbound_request, timeout=self.timeout_seconds
            ) as response:
                response_body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise SarvamAPIError(
                f"Sarvam returned HTTP {exc.code}: {body}",
                status_code=exc.code,
            ) from exc
        except error.URLError as exc:
            raise SarvamAPIError(f"Could not reach Sarvam: {exc.reason}") from exc

        try:
            decoded = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise SarvamAPIError("Sarvam returned a non-JSON response") from exc

        attempt_id = decoded.get("attempt_id") if isinstance(decoded, dict) else None
        if not isinstance(attempt_id, str) or not attempt_id:
            raise SarvamAPIError("Sarvam response did not contain an attempt_id")
        return attempt_id

