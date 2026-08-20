"""Sarvam-native caller speech synthesis for live Indus evaluation."""

from __future__ import annotations

import base64
import asyncio
import io
import os
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from sarvamai import AsyncSarvamAI


@dataclass(frozen=True)
class SynthesizedSpeech:
    pcm: bytes
    sample_rate: int
    provider: str
    model: str
    voice: str


class SpeechSynthesizer(Protocol):
    async def synthesize(self, text: str, language: str) -> SynthesizedSpeech: ...


class LocalSpeechSynthesizer:
    """Local caller-side TTS; Samvaad remains the audio-native agent under test."""

    async def synthesize(self, text: str, language: str) -> SynthesizedSpeech:
        voice = "Lekha" if language in {"hindi", "hinglish"} else "Aman"

        def render() -> bytes:
            with tempfile.TemporaryDirectory(prefix="loopline-caller-") as temp:
                aiff = Path(temp) / "caller.aiff"
                pcm = Path(temp) / "caller.pcm"
                subprocess.run(["say", "-v", voice, "-o", str(aiff), text], check=True, capture_output=True)
                subprocess.run(
                    ["ffmpeg", "-y", "-loglevel", "error", "-i", str(aiff), "-f", "s16le", "-acodec", "pcm_s16le", "-ac", "1", "-ar", "16000", str(pcm)],
                    check=True,
                    capture_output=True,
                )
                return pcm.read_bytes()

        return SynthesizedSpeech(
            pcm=await asyncio.to_thread(render),
            sample_rate=16000,
            provider="local_test_fixture",
            model="macos-say+ffmpeg",
            voice=voice,
        )


def _language_code(language: str) -> str:
    if language == "punjabi":
        return "pa-IN"
    return "en-IN" if language == "english" else "hi-IN"


def _wav_to_pcm(payload: bytes) -> tuple[bytes, int]:
    with wave.open(io.BytesIO(payload), "rb") as wav_file:
        if wav_file.getnchannels() != 1 or wav_file.getsampwidth() != 2:
            raise RuntimeError("Sarvam TTS returned unsupported WAV format; expected mono PCM16")
        sample_rate = wav_file.getframerate()
        pcm = wav_file.readframes(wav_file.getnframes())
    return pcm, sample_rate


class SarvamSpeechSynthesizer:
    """Optional Bulbul v3 caller fixture via the standard Sarvam SDK.

    This is not used by the default EVA-to-Samvaad path. It remains available
    only for a controlled caller-voice ablation. Voice Agents keys and standard
    speech keys are separate products.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        speaker: str = "priya",
        pace: float = 1.05,
    ) -> None:
        self.api_key = (api_key or os.environ.get("SARVAM_API_KEY", "")).strip()
        if not self.api_key:
            raise RuntimeError(
                "SARVAM_API_KEY is not set; create a standard Sarvam speech API key. "
                "Do not use SARVAM_VOICE_AGENTS_API_KEY here."
            )
        self.speaker = speaker
        self.pace = pace

    async def synthesize(self, text: str, language: str) -> SynthesizedSpeech:
        async with AsyncSarvamAI(api_subscription_key=self.api_key) as client:
            response = await client.text_to_speech.convert(
                text=text,
                language_code=_language_code(language),
                speaker=self.speaker,
                pace=self.pace,
                speech_sample_rate=16000,
                enable_preprocessing=True,
                model="bulbul:v3",
                output_audio_codec="wav",
            )
        if not response.audios:
            raise RuntimeError("Sarvam TTS returned no audio")
        wav_payload = base64.b64decode(response.audios[0])
        pcm, sample_rate = _wav_to_pcm(wav_payload)
        if sample_rate != 16000:
            raise RuntimeError(f"Sarvam TTS returned {sample_rate} Hz; expected 16000 Hz")
        return SynthesizedSpeech(
            pcm=pcm,
            sample_rate=sample_rate,
            provider="sarvam",
            model="bulbul:v3",
            voice=self.speaker,
        )
