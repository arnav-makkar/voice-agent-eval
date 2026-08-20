from __future__ import annotations

import json
import unittest

from sarvam_voice_agents.client import (
    SarvamVoiceAgentsClient,
    build_outbound_payload,
)
from sarvam_voice_agents.config import Settings


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def test_settings() -> Settings:
    return Settings(
        org_id="org-123",
        workspace_id="workspace-456",
        app_id="agent-789",
        app_version=1,
        connection_id="connection-321",
        agent_phone_number="+911111111111",
        user_phone_number="+912222222222",
        api_key="test-only-key",
    )


class PayloadTests(unittest.TestCase):
    def test_minimum_payload_omits_optional_blocks(self) -> None:
        payload = build_outbound_payload(test_settings())

        self.assertEqual(payload["app_config"]["app_type"], "agent")
        self.assertEqual(payload["app_config"]["app_version"], 1)
        self.assertNotIn("agent_variables", payload["app_config"])
        self.assertNotIn("app_overrides", payload["app_config"])
        self.assertNotIn("webhook_config", payload)

    def test_optional_blocks_match_generated_recipe(self) -> None:
        payload = build_outbound_payload(
            test_settings(),
            agent_variables={"userName": "Asha"},
            initial_bot_message="Hello Asha",
            initial_state_name="verify_identity",
            webhook_url="https://example.test/webhooks/sarvam",
            webhook_metadata={"lead_id": "lead-1"},
        )

        self.assertEqual(payload["app_config"]["agent_variables"]["userName"], "Asha")
        self.assertEqual(
            payload["app_config"]["app_overrides"]["initial_state_name"],
            "verify_identity",
        )
        self.assertEqual(payload["webhook_config"]["metadata"]["lead_id"], "lead-1")


class ClientTests(unittest.TestCase):
    def test_posts_to_exact_endpoint_and_returns_attempt_id(self) -> None:
        captured: dict[str, object] = {}

        def opener(outbound_request: object, *, timeout: float) -> FakeResponse:
            captured["request"] = outbound_request
            captured["timeout"] = timeout
            return FakeResponse({"attempt_id": "attempt-abc"})

        settings = test_settings()
        client = SarvamVoiceAgentsClient(
            api_key=settings.api_key,
            org_id=settings.org_id,
            workspace_id=settings.workspace_id,
            opener=opener,
        )
        attempt_id = client.create_outbound_call(build_outbound_payload(settings))

        outbound_request = captured["request"]
        self.assertEqual(attempt_id, "attempt-abc")
        self.assertEqual(
            outbound_request.full_url,
            "https://apps.sarvam.ai/api/outbounds/v1/orgs/org-123/"
            "workspaces/workspace-456/outbounds",
        )
        self.assertEqual(outbound_request.get_method(), "POST")
        headers = {key.lower(): value for key, value in outbound_request.header_items()}
        self.assertEqual(headers["content-type"], "application/json")
        self.assertEqual(headers["x-api-key"], "test-only-key")


if __name__ == "__main__":
    unittest.main()
