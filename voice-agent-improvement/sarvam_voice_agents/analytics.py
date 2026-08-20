"""Read-only Sarvam Voice Agents analytics client.

Endpoints match the official Analytics API:
https://docs.sarvam.ai/conversations/api/analytics/attempts
https://docs.sarvam.ai/conversations/api/analytics/transcripts
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

import requests

from .client import SarvamAPIError


ANALYTICS_BASE_URL = "https://apps.sarvam.ai/api/analytics/v1"


class SarvamAnalyticsClient:
    """Fetch attempts and transcripts without mutating the live agent."""

    def __init__(
        self,
        *,
        api_key: str,
        org_id: str,
        workspace_id: str,
        app_id: str,
        timeout_seconds: float = 30.0,
        session: requests.Session | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("A Voice Agents API key is required")
        self.api_key = api_key
        self.org_id = org_id
        self.workspace_id = workspace_id
        self.app_id = app_id
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    @property
    def app_analytics_url(self) -> str:
        return (
            f"{ANALYTICS_BASE_URL}/{self.org_id}/{self.workspace_id}/{self.app_id}"
        )

    @property
    def headers(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key}

    def _get_json(self, url: str, *, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = self.session.get(
                url,
                headers=self.headers,
                params=dict(params or {}),
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            detail = getattr(getattr(exc, "response", None), "text", "")
            suffix = f": {detail}" if detail else ""
            raise SarvamAPIError(
                f"Sarvam analytics request failed{suffix}", status_code=status
            ) from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise SarvamAPIError("Sarvam analytics returned non-JSON") from exc
        if not isinstance(payload, dict):
            raise SarvamAPIError("Sarvam analytics returned an invalid JSON shape")
        return payload

    def list_attempts(
        self,
        *,
        start_datetime: str,
        end_datetime: str,
        limit: int = 1000,
        offset: int = 0,
        sort_by: str = "start_datetime",
        sort_order: str = "asc",
    ) -> list[dict[str, Any]]:
        payload = self._get_json(
            f"{self.app_analytics_url}/attempts",
            params={
                "start_datetime": start_datetime,
                "end_datetime": end_datetime,
                "limit": limit,
                "offset": offset,
                "sort_by": sort_by,
                "sort_order": sort_order,
            },
        )
        items = payload.get("items")
        if not isinstance(items, list):
            raise SarvamAPIError("Sarvam attempts response did not contain items")
        return [item for item in items if isinstance(item, dict)]

    def get_transcript(self, interaction_id: str) -> dict[str, Any]:
        if not interaction_id:
            raise ValueError("interaction_id is required")
        encoded = quote(interaction_id, safe="")
        payload = self._get_json(f"{self.app_analytics_url}/transcripts/{encoded}")
        messages = payload.get("messages")
        if not isinstance(messages, list):
            raise SarvamAPIError("Sarvam transcript response did not contain messages")
        return payload


SENSITIVE_ATTEMPT_FIELDS = {
    "audio_url",
    "user_contact",
    "user_contact_hashed",
    "user_identifier",
}


def redact_attempt(attempt: Mapping[str, Any]) -> dict[str, Any]:
    """Drop direct identifiers and recording URLs from the analysis corpus."""

    redacted = {
        key: value
        for key, value in attempt.items()
        if key not in SENSITIVE_ATTEMPT_FIELDS
    }
    redacted["recording_available"] = bool(attempt.get("audio_url"))
    return redacted
