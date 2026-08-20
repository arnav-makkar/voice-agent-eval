from __future__ import annotations

import unittest

from sarvam_voice_agents.analytics import SarvamAnalyticsClient, redact_attempt


class FakeResponse:
    def __init__(self, value):
        self.value = value

    def raise_for_status(self):
        return None

    def json(self):
        return self.value


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(self.response)


class AnalyticsTests(unittest.TestCase):
    def client(self, response):
        return SarvamAnalyticsClient(
            api_key="test",
            org_id="org",
            workspace_id="workspace",
            app_id="agent",
            session=FakeSession(response),
        )

    def test_attempts_use_documented_endpoint(self):
        client = self.client({"items": [{"attempt_id": "a1"}]})
        items = client.list_attempts(
            start_datetime="2026-08-17T00:00:00Z",
            end_datetime="2026-08-18T00:00:00Z",
        )
        self.assertEqual(items[0]["attempt_id"], "a1")
        url, kwargs = client.session.calls[0]
        self.assertEqual(url, "https://apps.sarvam.ai/api/analytics/v1/org/workspace/agent/attempts")
        self.assertEqual(kwargs["params"]["limit"], 1000)

    def test_transcript_encodes_interaction_id(self):
        client = self.client({"interaction_id": "date/id", "messages": []})
        client.get_transcript("date/id:time")
        url, _ = client.session.calls[0]
        self.assertTrue(url.endswith("/transcripts/date%2Fid%3Atime"))

    def test_redaction_drops_direct_identifiers(self):
        attempt = redact_attempt({
            "attempt_id": "a1",
            "user_contact": "+910000000000",
            "user_identifier": "secret",
            "user_contact_hashed": "hash",
            "audio_url": "https://signed.example/audio",
            "user_contact_masked": "+91******0000",
        })
        self.assertNotIn("user_contact", attempt)
        self.assertNotIn("audio_url", attempt)
        self.assertTrue(attempt["recording_available"])
        self.assertEqual(attempt["user_contact_masked"], "+91******0000")


if __name__ == "__main__":
    unittest.main()
