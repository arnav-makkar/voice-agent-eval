import json
import base64
import tempfile
import unittest
from pathlib import Path

from framework.adapters.gemini import GeminiJsonClient


class FakeResponse:
    ok = True
    status_code = 200
    text = ""

    def json(self):
        return {
            "candidates": [{"content": {"parts": [{"text": json.dumps({"ready": True})}]}}],
            "modelVersion": "gemini-test",
            "usageMetadata": {"promptTokenCount": 4, "candidatesTokenCount": 2},
        }


class FakeSession:
    def __init__(self):
        self.calls = 0

    def post(self, *args, **kwargs):
        self.calls += 1
        self.last = (args, kwargs)
        return FakeResponse()


class GeminiAdapterTests(unittest.TestCase):
    def test_structured_call_is_cached_without_storing_key(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            session = FakeSession()
            client = GeminiJsonClient(api_key="secret-test-key", cache_dir=Path(temporary), session=session)
            schema = {"type": "object", "properties": {"ready": {"type": "boolean"}}, "required": ["ready"]}
            first = client.complete_json(system="Return JSON", user="Ready?", response_schema=schema)
            second = client.complete_json(system="Return JSON", user="Ready?", response_schema=schema)
            self.assertTrue(first.data["ready"])
            self.assertEqual(session.calls, 1)
            self.assertTrue(second.metadata["cache_hit"])
            cache_text = "".join(path.read_text() for path in Path(temporary).rglob("*.json"))
            self.assertNotIn("secret-test-key", cache_text)

    def test_audio_call_uses_inline_wav_and_records_only_audio_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            session = FakeSession()
            client = GeminiJsonClient(api_key="secret-test-key", cache_dir=Path(temporary), session=session)
            wav = b"RIFF-test-wave"
            schema = {"type": "object", "properties": {"ready": {"type": "boolean"}}, "required": ["ready"]}
            result = client.complete_audio_json(
                system="Listen",
                user="Respond",
                audio_wav=wav,
                response_schema=schema,
            )
            body = session.last[1]["json"]
            inline = body["contents"][0]["parts"][1]["inlineData"]
            self.assertEqual(inline["mimeType"], "audio/wav")
            self.assertEqual(base64.b64decode(inline["data"]), wav)
            self.assertEqual(result.metadata["audio_bytes"], len(wav))
            cache_text = "".join(path.read_text() for path in Path(temporary).rglob("*.json"))
            self.assertNotIn(base64.b64encode(wav).decode("ascii"), cache_text)


if __name__ == "__main__":
    unittest.main()
