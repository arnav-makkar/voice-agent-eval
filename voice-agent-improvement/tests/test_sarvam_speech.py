import io
import tempfile
import unittest
import wave
from pathlib import Path

from framework.evaluation.adapters.sarvam_speech import _language_code, _wav_to_pcm
from framework.evaluation.adapters.indus import _pcm_to_wav_bytes, _resample_pcm16, _write_duplex_wav, _write_webvtt


class SarvamSpeechTests(unittest.TestCase):
    def test_language_mapping(self):
        self.assertEqual(_language_code("hinglish"), "hi-IN")
        self.assertEqual(_language_code("english"), "en-IN")
        self.assertEqual(_language_code("punjabi"), "pa-IN")

    def test_pcm16_wav_decoding(self):
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(b"\x01\x00\xff\xff")
        pcm, rate = _wav_to_pcm(buffer.getvalue())
        self.assertEqual(rate, 16000)
        self.assertEqual(pcm, b"\x01\x00\xff\xff")

    def test_duplex_evidence_writes_audio_and_captions(self):
        with tempfile.TemporaryDirectory() as temp:
            audio = Path(temp) / "call.wav"
            captions = Path(temp) / "call.wav.vtt"
            _write_duplex_wav(audio, [(0.0, b"\x01\x00" * 160, 16000), (0.01, b"\x01\x00" * 160, 16000)])
            _write_webvtt(
                captions,
                [
                    {"kind": "transcript", "role": "bot", "text": "Hello", "offset_ms": 0},
                    {"kind": "caller_audio_start", "text": "Haan", "offset_ms": 900},
                ],
            )
            with wave.open(str(audio), "rb") as wav_file:
                self.assertEqual(wav_file.getframerate(), 16000)
                self.assertGreater(wav_file.getnframes(), 160)
            body = captions.read_text(encoding="utf-8")
            self.assertIn("WEBVTT", body)
            self.assertIn("Agent: Hello", body)
            self.assertIn("Caller: Haan", body)

    def test_agent_pcm_is_normalized_and_wrapped_for_audio_reasoning(self):
        source_8k = b"\x01\x00" * 80
        normalized = _resample_pcm16(source_8k, 8000, 16000)
        self.assertEqual(len(normalized), len(source_8k) * 2)
        wav_bytes = _pcm_to_wav_bytes(normalized, 16000)
        with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
            self.assertEqual(wav_file.getframerate(), 16000)
            self.assertEqual(wav_file.getnchannels(), 1)
            self.assertEqual(wav_file.readframes(wav_file.getnframes()), normalized)


if __name__ == "__main__":
    unittest.main()
