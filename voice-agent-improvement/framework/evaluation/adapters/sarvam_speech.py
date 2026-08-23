"""Caller speech synthesis for live Indus evaluation.

Three providers behind one protocol. The caller's *brain* is always the
scenario-faithful adaptive policy; only its *voice* changes here, so swapping
providers never changes what the caller says or intends — only how it sounds to
the agent's ASR.
"""

from __future__ import annotations

import asyncio
import base64
import json
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


ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech"
# Rajesh — Indian male, calm and controlled. Already provisioned for this project
# by scripts/provision_eva_elevenlabs_caller.py, so the caller sounds the same
# whichever ElevenLabs path is used.
DEFAULT_ELEVENLABS_VOICE = "n32p8A7EZ9CiVeRYpBY9"


class ElevenLabsSpeechSynthesizer:
    """Natural caller speech, so ASR error is the agent's to own rather than ours.

    The default local fixture is macOS ``say``, which produces flat, non-native
    prosody. When the agent mishears that, the failure belongs to the test rig,
    not to the agent — and a baseline that cannot separate the two is the same
    class of mistake as scoring a dead tunnel as agent silence. A neutral Indian
    voice removes the confound.

    One voice is used for every scenario on purpose. Varying the voice would add
    an uncontrolled variable across a matched BASE/IMPROVED comparison.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        voice_id: str = DEFAULT_ELEVENLABS_VOICE,
        model_id: str = "eleven_multilingual_v2",
        stability: float = 0.55,
        similarity_boost: float = 0.8,
        speed: float = 1.0,
    ) -> None:
        self.api_key = (api_key or os.environ.get("ELEVENLABS_API_KEY", "")).strip()
        if not self.api_key:
            raise RuntimeError("ELEVENLABS_API_KEY is not set; required for the ElevenLabs caller voice.")
        self.voice_id = voice_id
        self.model_id = model_id
        self.stability = stability
        self.similarity_boost = similarity_boost
        self.speed = speed

    async def synthesize(self, text: str, language: str) -> SynthesizedSpeech:
        def render() -> bytes:
            import ssl
            import urllib.request

            import certifi

            body = json.dumps(
                {
                    "text": text,
                    "model_id": self.model_id,
                    "voice_settings": {
                        "stability": self.stability,
                        "similarity_boost": self.similarity_boost,
                        "speed": self.speed,
                    },
                }
            ).encode("utf-8")
            request = urllib.request.Request(
                # pcm_16000 matches what the duplex path streams to Samvaad, so no
                # resampling step can quietly degrade the caller audio.
                f"{ELEVENLABS_TTS_URL}/{self.voice_id}?output_format=pcm_16000",
                data=body,
                method="POST",
                headers={
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/pcm",
                },
            )
            context = ssl.create_default_context(cafile=certifi.where())
            with urllib.request.urlopen(request, timeout=45, context=context) as response:
                return response.read()

        pcm = await asyncio.to_thread(render)
        if not pcm:
            raise RuntimeError("ElevenLabs TTS returned no audio")
        return SynthesizedSpeech(
            pcm=pcm,
            sample_rate=16000,
            provider="elevenlabs",
            model=self.model_id,
            voice=self.voice_id,
        )
