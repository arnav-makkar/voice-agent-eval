"""Official Sarvam Voice Agents SDK adapter for live multi-turn evaluation.

The adapter deliberately uses the installed SDK rather than duplicating or
guessing Sarvam's signed-WebSocket protocol. Raw server frames are retained so
tool, variable, language, and state events remain auditable even when a given
SDK release does not yet expose a typed callback for every event.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import copy
import hashlib
import io
import json
import os
import random
import subprocess
import tempfile
import time
import uuid
import wave
from array import array
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import SecretStr
import certifi
from sarvam_conv_ai_sdk import AsyncSamvaadAgent, InteractionConfig, InteractionType
from sarvam_conv_ai_sdk.messages.text import ServerTextChunkMsg
from sarvam_conv_ai_sdk.messages.types import MsgStatus, UserIdentifierType

from framework.adapters.gemini import load_env_file
from framework.core.io import read_jsonl, write_json, write_jsonl
from framework.evaluation.adaptive_caller import AdaptiveCallerPolicy, CallerAction, GeminiAdaptiveCallerPolicy
from framework.evaluation.adapters.sarvam_speech import LocalSpeechSynthesizer, SarvamSpeechSynthesizer, SpeechSynthesizer
from framework.evaluation.contracts import ConversationTurn, EvaluationScenario, ScenarioRun, ToolEvent
from framework.evaluation.environment import EMIEnvironment, ToolExecutionError
from framework.evaluation.live_budget import LiveBudgetLedger, LiveReservation
from framework.evaluation.metrics import aggregate, evaluate_run
from framework.evaluation.runner import load_scenarios
from sarvam_voice_agents.config import Settings


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCENARIOS = ROOT / "artifacts" / "framework" / "emi" / "dynamic_scenarios_v1" / "development.jsonl"
DEFAULT_OUTPUT = ROOT / "artifacts" / "framework" / "emi" / "indus_chat_smoke"
DUPLEX_EVALUATOR_VERSION = "evaluation-metrics.v3/loopline-eva-adapter.v1/samvaad-duplex.v8"
DEFAULT_DUPLEX_FREEZE = ROOT / "artifacts" / "framework" / "emi" / "eva_adapter_v8" / "evaluator_freeze.json"


class TracingSamvaadAgent(AsyncSamvaadAgent):
    """Capture the raw SDK frames before normal typed routing."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.raw_messages: list[dict[str, Any]] = []

    async def _route_message(self, message: dict[str, Any]) -> None:  # noqa: SLF001 - audit shim around pinned SDK
        self.raw_messages.append(copy.deepcopy(message))
        await super()._route_message(message)


def _find_value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        if key in value:
            return value[key]
        for child in value.values():
            found = _find_value(child, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_value(child, key)
            if found is not None:
                return found
    return None


def _runtime_tool_events(raw_messages: list[dict[str, Any]]) -> list[ToolEvent]:
    events: list[ToolEvent] = []
    for message in raw_messages:
        if message.get("type") != "server.event.tool_call":
            continue
        name = _find_value(message, "tool_name") or _find_value(message, "name") or "unknown"
        arguments = _find_value(message, "arguments") or _find_value(message, "parameters") or {}
        result = _find_value(message, "result") or _find_value(message, "output") or {}
        status = str(_find_value(message, "status") or "observed")
        events.append(ToolEvent(len(events) + 1, str(name), dict(arguments) if isinstance(arguments, dict) else {"raw": arguments}, dict(result) if isinstance(result, dict) else {"raw": result}, status))
    return events


def _runtime_variables(raw_messages: list[dict[str, Any]]) -> dict[str, Any]:
    variables: dict[str, Any] = {}
    for message in raw_messages:
        if message.get("type") != "server.event.variable_update":
            continue
        update = _find_value(message, "variables") or _find_value(message, "agent_variables") or _find_value(message, "updates")
        if isinstance(update, dict):
            variables.update(update)
    return variables


def synthesize_caller_pcm(text: str, language: str) -> bytes:
    """Use the local macOS voice to produce PCM16 mono 16 kHz test speech."""
    voice = "Lekha" if language in {"hindi", "hinglish"} else "Aman"
    with tempfile.TemporaryDirectory(prefix="loopline-tts-") as temp:
        aiff = Path(temp) / "caller.aiff"
        pcm = Path(temp) / "caller.pcm"
        subprocess.run(["say", "-v", voice, "-o", str(aiff), text], check=True, capture_output=True)
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(aiff), "-f", "s16le", "-acodec", "pcm_s16le", "-ac", "1", "-ar", "16000", str(pcm)],
            check=True,
            capture_output=True,
        )
        return pcm.read_bytes()


def _redact_raw_messages(raw_messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    redacted = []
    for message in raw_messages:
        item = copy.deepcopy(message)
        if "audio_base64" in item:
            item["audio_bytes"] = len(base64.b64decode(str(item.pop("audio_base64"))))
            item["audio_redacted"] = True
        redacted.append(item)
    return redacted


def _pcm_rms(data: bytes) -> float:
    samples = array("h")
    samples.frombytes(data)
    if not samples:
        return 0.0
    return (sum(sample * sample for sample in samples) / len(samples)) ** 0.5


def apply_pcm_perturbations(pcm: bytes, perturbations: list[str], *, seed: int = 23) -> bytes:
    """Apply deterministic, auditable caller-channel stress conditions.

    These are intentionally small signal transforms rather than a claim of full
    tau-Voice reproduction. The exact ordered labels are retained in each trace.
    """
    samples = array("h")
    samples.frombytes(pcm)
    values = list(samples)
    rng = random.Random(seed)
    for perturbation in perturbations:
        if perturbation == "low_volume_12db":
            values = [int(sample * 0.25) for sample in values]
        elif perturbation == "background_noise_12db":
            signal_rms = (_pcm_rms(array("h", values).tobytes()) or 1.0)
            noise_rms = signal_rms / (10 ** (12 / 20))
            values = [max(-32768, min(32767, int(sample + rng.gauss(0, noise_rms)))) for sample in values]
        elif perturbation == "fast_speech_1_25x":
            # Deterministic nearest-neighbour time compression while retaining
            # 16 kHz output expected by the Sarvam CALL runtime.
            output_length = max(1, int(len(values) / 1.25))
            values = [values[min(len(values) - 1, int(index * 1.25))] for index in range(output_length)]
        elif perturbation == "packet_loss_5pct":
            chunk = 320  # 20 ms at 16 kHz
            for start in range(0, len(values), chunk):
                if rng.random() < 0.05:
                    values[start : start + chunk] = [0] * len(values[start : start + chunk])
        elif perturbation in {"language_switch", "barge_in_text_proxy", "clean"}:
            continue
        else:
            raise ValueError(f"unsupported audio perturbation: {perturbation}")
    result = array("h", values)
    return result.tobytes()


async def _stream_pcm(agent: AsyncSamvaadAgent, pcm: bytes, sample_rate: int = 16000) -> tuple[float, float]:
    """Stream realtime PCM chunks so the CALL runtime's VAD observes a turn."""
    chunk_bytes = int(sample_rate * 0.02) * 2
    for offset in range(0, len(pcm), chunk_bytes):
        await agent.send_audio(pcm[offset : offset + chunk_bytes])
        await asyncio.sleep(0.02)
    speech_content_ended_at = time.perf_counter()
    # The CALL runtime's VAD needs realtime silence to close the caller turn.
    silence = b"\x00" * chunk_bytes
    for _ in range(50):
        await agent.send_audio(silence)
        await asyncio.sleep(0.02)
    return speech_content_ended_at, time.perf_counter()


async def _wait_until_clear(event: asyncio.Event, timeout: float) -> bool:
    """Wait until an event clears; return False on timeout."""
    deadline = time.perf_counter() + timeout
    while event.is_set():
        if time.perf_counter() >= deadline:
            return False
        await asyncio.sleep(0.02)
    return True


def _resample_pcm16(pcm: bytes, source_rate: int, target_rate: int = 16000) -> bytes:
    if source_rate == target_rate:
        return pcm
    source = array("h")
    source.frombytes(pcm)
    if not source:
        return b""
    output_length = max(1, round(len(source) * target_rate / source_rate))
    output = array(
        "h",
        (
            source[min(len(source) - 1, int(index * source_rate / target_rate))]
            for index in range(output_length)
        ),
    )
    return output.tobytes()


def _write_duplex_wav(
    path: Path,
    segments: list[tuple[float, bytes, int]],
    *,
    sample_rate: int = 16000,
) -> None:
    prepared: list[tuple[int, array]] = []
    total_samples = 1
    for offset_seconds, pcm, source_rate in segments:
        samples = array("h")
        samples.frombytes(_resample_pcm16(pcm, source_rate, sample_rate))
        offset = max(0, round(offset_seconds * sample_rate))
        prepared.append((offset, samples))
        total_samples = max(total_samples, offset + len(samples))
    mixed = array("h", [0]) * total_samples
    for offset, samples in prepared:
        for index, sample in enumerate(samples):
            mixed[offset + index] = max(-32768, min(32767, mixed[offset + index] + sample))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(mixed.tobytes())


def _pcm_to_wav_bytes(pcm: bytes, sample_rate: int = 16000) -> bytes:
    """Wrap mono PCM16 in a WAV container for multimodal audit inference."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm)
    buffer.seek(0)
    return buffer.read()


def _vtt_timestamp(milliseconds: float) -> str:
    total_ms = max(0, round(milliseconds))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def _write_webvtt(path: Path, events: list[dict[str, Any]]) -> None:
    captions = [
        item
        for item in events
        if item.get("text")
        and item.get("kind") in {"transcript", "simulator_audio_transcript", "caller_audio_start"}
    ]
    lines = ["WEBVTT", ""]
    for index, item in enumerate(captions, start=1):
        start = float(item.get("offset_ms", 0))
        next_start = float(captions[index].get("offset_ms", start + 4_000)) if index < len(captions) else start + 4_000
        end = max(start + 800, min(start + 6_000, next_start - 50))
        role = (
            "Agent"
            if (item.get("kind") == "transcript" and item.get("role") == "bot")
            or item.get("kind") == "simulator_audio_transcript"
            else "Caller"
        )
        lines.extend([str(index), f"{_vtt_timestamp(start)} --> {_vtt_timestamp(end)}", f"{role}: {item['text']}", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


async def run_adaptive_indus_scenario(
    scenario: EvaluationScenario,
    settings: Settings,
    *,
    caller_policy: AdaptiveCallerPolicy,
    speech_synthesizer: SpeechSynthesizer,
    response_timeout_seconds: float = 35.0,
    media_output: Path | None = None,
) -> tuple[ScenarioRun, list[dict[str, Any]]]:
    """Run one adaptive, audio-in/audio-out Indus session.

    Samvaad is the complete system under test. The caller simulator consumes
    Samvaad's returned audio directly; provider transcripts are optional audit
    evidence, never a control dependency. Audio callbacks remain active while
    caller PCM is sent, and barge-in is counted only when audio really overlaps.
    """
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    started = datetime.now(UTC)
    clock_started = time.perf_counter()
    run_id = f"INDUS-DUPLEX-{started.strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}"
    bot_queue: asyncio.Queue[tuple[str, float]] = asyncio.Queue()
    # pcm16@16k, speech-start time, speech-complete time
    audio_turn_queue: asyncio.Queue[tuple[bytes, int, float, float]] = asyncio.Queue()
    agent_speaking = asyncio.Event()
    interaction_ended = asyncio.Event()
    audio_buffer = bytearray()
    audio_silence_ms = 0.0
    agent_audio_started_at: float | None = None
    observed_user_transcripts: list[str] = []
    observed_bot_transcripts: list[str] = []
    observed_user_turn_transcripts: list[str] = []
    simulator_audio_transcripts: list[dict[str, Any]] = []
    emitted_bot_text: set[str] = set()
    transport_events: list[dict[str, Any]] = []
    media_segments: list[tuple[float, bytes, int]] = []
    caller_actions: list[dict[str, Any]] = []
    turns: list[ConversationTurn] = []
    history: list[dict[str, str]] = []

    def stamp(kind: str, **details: Any) -> None:
        transport_events.append(
            {"kind": kind, "offset_ms": round((time.perf_counter() - clock_started) * 1000, 1), **details}
        )

    async def handle_event(event: Any) -> None:
        event_type = str(getattr(event, "type", ""))
        stamp("sdk_event", event_type=event_type)
        if event_type == "server.action.interaction_end":
            await finish_agent_audio()
            interaction_ended.set()

    async def finish_agent_audio() -> None:
        nonlocal audio_silence_ms, agent_audio_started_at
        if not audio_buffer or agent_audio_started_at is None:
            return
        captured = bytes(audio_buffer)
        completed_at = time.perf_counter()
        audio_buffer.clear()
        audio_silence_ms = 0.0
        started_at = agent_audio_started_at
        agent_audio_started_at = None
        agent_speaking.clear()
        stamp("agent_audio_end", bytes=len(captured), sample_rate=16000)
        await audio_turn_queue.put((captured, 16000, started_at, completed_at))

    async def handle_audio(message: Any) -> None:
        nonlocal audio_silence_ms, agent_audio_started_at
        if not message.audio_base64:
            return
        data = base64.b64decode(message.audio_base64)
        sample_rate = int(message.sample_rate or 8000)
        media_segments.append((time.perf_counter() - clock_started, data, sample_rate))
        rms = _pcm_rms(data)
        duration_ms = len(data) / (2 * sample_rate) * 1000
        normalized = _resample_pcm16(data, sample_rate, 16000)
        if rms > 20:
            if not agent_speaking.is_set():
                audio_buffer.clear()
                agent_speaking.set()
                agent_audio_started_at = time.perf_counter()
                stamp("agent_audio_start", sample_rate=sample_rate)
            audio_silence_ms = 0.0
            audio_buffer.extend(normalized)
        elif agent_speaking.is_set():
            audio_buffer.extend(normalized)
            audio_silence_ms += duration_ms
            if audio_silence_ms >= 800:
                await finish_agent_audio()

    async def handle_transcript(message: Any) -> None:
        role = str(getattr(message, "role", ""))
        content = str(getattr(message, "content", "")).strip()
        if not content:
            return
        stamp("transcript", role=role, text=content)
        if role == "bot":
            observed_bot_transcripts.append(content)
            normalized = " ".join(content.lower().split())
            if normalized not in emitted_bot_text:
                emitted_bot_text.add(normalized)
                await bot_queue.put((content, time.perf_counter()))
        elif role == "user":
            observed_user_transcripts.append(content)

    config = InteractionConfig(
        user_identifier_type=UserIdentifierType.CUSTOM,
        user_identifier=f"eval:{run_id}:{scenario.scenario_id}",
        org_id=settings.org_id,
        workspace_id=settings.workspace_id,
        app_id=settings.app_id,
        version=settings.app_version,
        interaction_type=InteractionType.CALL,
        sample_rate=16000,
        agent_variables=dict(scenario.visible_context),
    )
    agent = TracingSamvaadAgent(
        api_key=SecretStr(settings.api_key),
        config=config,
        audio_callback=handle_audio,
        event_callback=handle_event,
        transcript_callback=handle_transcript,
    )
    environment = EMIEnvironment.from_initial(scenario.initial_environment)
    termination = "max_turns"
    latest_agent_text = ""
    pending_agent_audio: tuple[bytes, int, float, float] | None = None
    audio_agent_turns = 0
    last_caller_audio_end: float | None = None
    try:
        await agent.start()
        connected = await agent.wait_for_connect(timeout=15.0)
        if not connected:
            raise RuntimeError("Indus SDK did not connect within 15 seconds")
        stamp("connected", interaction_id=agent.get_interaction_id())
        try:
            pending_agent_audio = await asyncio.wait_for(audio_turn_queue.get(), timeout=8.0)
        except asyncio.TimeoutError:
            stamp("opening_timeout")

        for caller_turn in range(1, scenario.max_agent_turns + 1):
            if interaction_ended.is_set() and pending_agent_audio is None:
                termination = "agent_terminal"
                break
            audio_wav: bytes | None = None
            audio_started_at: float | None = None
            audio_completed_at: float | None = None
            if pending_agent_audio is not None:
                captured, captured_rate, audio_started_at, audio_completed_at = pending_agent_audio
                audio_wav = _pcm_to_wav_bytes(captured, captured_rate)

            # When no opening audio is available, the caller's first move is
            # deterministic scenario truth. This avoids spending another model
            # call to rediscover a known first utterance. Later moves are always
            # conditioned on the audio Samvaad actually returned.
            if caller_turn == 1 and audio_wav is None:
                first_step = scenario.user_steps[0]
                action = CallerAction(
                    "barge_in" if "barge_in_text_proxy" in scenario.perturbations else "speak",
                    first_step.text,
                    rationale="No completed opening audio; begin with the scenario-faithful first caller move.",
                    policy_node="initial-scenario-step",
                )
            else:
                try:
                    action = await caller_policy.next_action(
                        scenario=scenario,
                        history=list(history),
                        observed_agent_text=latest_agent_text,
                        observed_agent_audio_wav=audio_wav,
                        turn_index=caller_turn,
                    )
                except Exception as exc:
                    stamp("simulator_policy_error", error_type=type(exc).__name__, message=str(exc)[:400])
                    termination = "simulator_policy_error"
                    break

            if pending_agent_audio is not None:
                latest_agent_text = action.heard_agent_text.strip()
                transcript_text = latest_agent_text or "[agent audio captured; simulator transcript unavailable]"
                latency_origin = last_caller_audio_end if last_caller_audio_end is not None else clock_started
                latency_ms = round(((audio_started_at or audio_completed_at or latency_origin) - latency_origin) * 1000, 1)
                turns.append(ConversationTurn(len(turns) + 1, "agent", transcript_text, max(0.0, latency_ms)))
                history.append({"role": "agent", "content": transcript_text})
                transcript_record = {
                    "text": transcript_text,
                    "language": action.heard_language,
                    "audio_quality": action.audio_quality,
                    "source": "gemini_simulator_heard_samvaad_audio",
                    "audio_sha256": action.decision_metadata.get("audio_sha256"),
                    "model": action.decision_metadata.get("model_version"),
                }
                simulator_audio_transcripts.append(transcript_record)
                stamp(
                    "simulator_audio_transcript",
                    text=transcript_text,
                    role="bot",
                    language=action.heard_language,
                    audio_quality=action.audio_quality,
                    source=transcript_record["source"],
                )
                audio_agent_turns += 1
                pending_agent_audio = None

            action_record = {
                "turn_index": caller_turn,
                "action": action.action,
                "text": action.text,
                "delay_ms": action.delay_ms,
                "rationale": action.rationale,
                "policy_node": action.policy_node,
                "heard_agent_text": action.heard_agent_text,
                "heard_language": action.heard_language,
                "audio_quality": action.audio_quality,
                "decision": {
                    key: action.decision_metadata.get(key)
                    for key in (
                        "adapter_version",
                        "model_version",
                        "request_hash",
                        "response_hash",
                        "audio_sha256",
                        "audio_bytes",
                        "latency_ms",
                        "usage",
                    )
                    if action.decision_metadata.get(key) is not None
                },
            }
            if action.delay_ms:
                await asyncio.sleep(action.delay_ms / 1000)
            if action.action == "end":
                action_record["observed_overlap"] = False
                caller_actions.append(action_record)
                termination = "caller_terminal"
                break
            if action.action == "wait":
                action_record["observed_overlap"] = False
                caller_actions.append(action_record)
                stamp("caller_wait", delay_ms=action.delay_ms)
                try:
                    pending_agent_audio = await asyncio.wait_for(audio_turn_queue.get(), timeout=response_timeout_seconds)
                    continue
                except asyncio.TimeoutError:
                    termination = "response_timeout"
                    break

            speech = await speech_synthesizer.synthesize(action.text, scenario.language)
            if speech.sample_rate != 16000:
                raise RuntimeError(f"caller synthesizer returned {speech.sample_rate} Hz; expected 16000 Hz")
            if action.action == "speak":
                await _wait_until_clear(agent_speaking, timeout=8.0)
            else:
                # Give an early transcript a short chance to align with live
                # audio. The overlap flag is evidence, not simulator intent.
                if not agent_speaking.is_set():
                    try:
                        await asyncio.wait_for(agent_speaking.wait(), timeout=0.75)
                    except asyncio.TimeoutError:
                        pass
            observed_overlap = agent_speaking.is_set()
            action_record.update(
                {
                    "observed_overlap": observed_overlap,
                    "speech_provider": speech.provider,
                    "speech_model": speech.model,
                    "speech_voice": speech.voice,
                    "pcm_bytes": len(speech.pcm),
                }
            )
            caller_actions.append(action_record)
            stamp("caller_audio_start", action=action.action, overlap=observed_overlap, text=action.text)
            media_segments.append((time.perf_counter() - clock_started, speech.pcm, speech.sample_rate))
            turns.append(ConversationTurn(len(turns) + 1, "caller", action.text))
            history.append({"role": "caller", "content": action.text})
            speech_content_ended_at, vad_close_ended_at = await _stream_pcm(
                agent,
                apply_pcm_perturbations(speech.pcm, scenario.perturbations, seed=23 + caller_turn),
                sample_rate=speech.sample_rate,
            )
            sent_at = speech_content_ended_at
            last_caller_audio_end = sent_at
            observed_user_turn_transcripts.append(observed_user_transcripts[-1] if observed_user_transcripts else "")
            action_record["provider_transcript_snapshot"] = observed_user_turn_transcripts[-1]
            stamp(
                "caller_audio_end",
                action=action.action,
                speech_content_offset_ms=round((speech_content_ended_at - clock_started) * 1000, 1),
                vad_close_offset_ms=round((vad_close_ended_at - clock_started) * 1000, 1),
            )
            try:
                deadline = time.perf_counter() + response_timeout_seconds
                while True:
                    remaining = max(0.01, deadline - time.perf_counter())
                    candidate_audio = await asyncio.wait_for(audio_turn_queue.get(), timeout=remaining)
                    _pcm, _rate, candidate_started, candidate_completed = candidate_audio
                    # Audio that began before the caller finished speaking is
                    # either an overlapping opening/prompt or the interrupted
                    # prior turn. It is duplex evidence, but not the response
                    # caused by this caller move.
                    if candidate_started < sent_at:
                        stamp(
                            "interrupted_agent_audio",
                            requested_barge_in=action.action == "barge_in",
                            started_before_caller_end=True,
                            completed_after_caller_end=candidate_completed > sent_at,
                            bytes=len(_pcm),
                        )
                        continue
                    pending_agent_audio = candidate_audio
                    break
            except asyncio.TimeoutError:
                termination = "response_timeout"
                break
    finally:
        await agent.stop()
        await finish_agent_audio()

    runtime_variables = _runtime_variables(agent.raw_messages)
    disposition = str(runtime_variables.get("disposition") or "call_disconnected")
    try:
        if disposition != "call_disconnected":
            environment.execute("record_disposition", {"disposition": disposition})
    except ToolExecutionError:
        pass
    hidden_markers = {scenario.scenario_id.lower(), *(str(key).lower() for key in scenario.hidden_state)}
    caller_text = " ".join(turn.content for turn in turns if turn.actor == "caller").lower()
    leaks = sorted(marker for marker in hidden_markers if marker and marker in caller_text)
    requested_barge_ins = sum(item["action"] == "barge_in" for item in caller_actions)
    observed_barge_ins = sum(bool(item.get("observed_overlap")) for item in caller_actions if item["action"] == "barge_in")
    tool_events = _runtime_tool_events(agent.raw_messages)
    audio_artifact: str | None = None
    caption_artifact: str | None = None
    if media_output is not None and media_segments:
        audio_path = media_output / f"{run_id}.wav"
        caption_path = media_output / f"{run_id}.wav.vtt"
        _write_duplex_wav(audio_path, media_segments)
        _write_webvtt(caption_path, transport_events)
        audio_artifact = str(audio_path)
        caption_artifact = str(caption_path)
    run = ScenarioRun(
        schema_version="scenario-run.v1",
        run_id=run_id,
        scenario_id=scenario.scenario_id,
        candidate_id=f"indus-v{settings.app_version}",
        candidate_hash=hashlib.sha256(f"{settings.app_id}:v{settings.app_version}".encode()).hexdigest(),
        adapter="sarvam_conv_ai_sdk.call.adaptive_duplex",
        started_at=started.isoformat(),
        ended_at=datetime.now(UTC).isoformat(),
        termination_reason=termination,
        interaction_id=agent.get_interaction_id(),
        turns=turns,
        tool_events=tool_events,
        initial_state=scenario.initial_environment,
        final_state={**environment.snapshot(), "runtime_variables": runtime_variables},
        agent_declared_disposition=disposition,
        simulator_validation={
            "passed": bool(turns)
            and audio_agent_turns > 0
            and not leaks
            and termination not in {"response_timeout", "simulator_policy_error"},
            "adaptive_policy": True,
            "hidden_state_leaks": leaks,
            "requested_barge_ins": requested_barge_ins,
            "observed_barge_ins": observed_barge_ins,
            "caller_turns": sum(turn.actor == "caller" for turn in turns),
            "observed_user_transcripts": len(observed_user_transcripts),
            "agent_audio_turns": audio_agent_turns,
            "agent_text_source": "gemini_simulator_heard_samvaad_audio",
        },
        provenance={
            "sdk": "sarvam-conv-ai-sdk==1.0.21",
            "interaction_type": "call",
            "execution_mode": "adaptive_audio_duplex",
            "app_id": settings.app_id,
            "app_version": settings.app_version,
            "raw_message_count": len(agent.raw_messages),
            "raw_message_types": sorted({str(message.get("type")) for message in agent.raw_messages}),
            "observed_user_transcripts": observed_user_transcripts,
            "observed_user_turn_transcripts": observed_user_turn_transcripts,
            "observed_bot_transcripts": observed_bot_transcripts,
            "simulator_audio_transcripts": simulator_audio_transcripts,
            "caller_actions": caller_actions,
            "transport_events": transport_events,
            "audio_artifact": audio_artifact,
            "caption_artifact": caption_artifact,
            "audio_perturbations": scenario.perturbations,
            "latency_semantics": "end_of_user_audio_to_first_sample_of_next_samvaad_agent_audio",
            "control_signal": "samvaad_returned_audio",
            "system_under_test": "Sarvam Samvaad/Indus audio-native voice agent",
            "simulator_boundary": "Gemini hears returned Samvaad audio and selects caller behavior; it is not the target agent",
            "evaluator_version": DUPLEX_EVALUATOR_VERSION,
        },
    )
    return run, _redact_raw_messages(agent.raw_messages)


async def run_indus_scenario(
    scenario: EvaluationScenario,
    settings: Settings,
    *,
    response_timeout_seconds: float = 35.0,
    interaction_type: InteractionType = InteractionType.CHAT,
) -> tuple[ScenarioRun, list[dict[str, Any]]]:
    # The python.org macOS runtime may not be wired to the system keychain.
    # Use certifi's CA bundle; never bypass TLS verification.
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    started = datetime.now(UTC)
    run_id = f"INDUS-{started.strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}"
    text_queue: asyncio.Queue[tuple[str, float]] = asyncio.Queue()
    audio_turn_queue: asyncio.Queue[tuple[bytes, int, float]] = asyncio.Queue()
    chunk_buffer: list[str] = []
    audio_buffer = bytearray()
    audio_speech_started = False
    audio_silence_ms = 0.0
    observed_user_transcripts: list[str] = []
    turns: list[ConversationTurn] = []
    interaction_ended = asyncio.Event()

    async def handle_text(message: Any) -> None:
        text = str(message.text)
        if isinstance(message, ServerTextChunkMsg):
            chunk_buffer.append(text)
            if message.status == MsgStatus.COMPLETED:
                combined = "".join(chunk_buffer).strip()
                chunk_buffer.clear()
                if combined:
                    await text_queue.put((combined, time.perf_counter()))
        elif text.strip():
            await text_queue.put((text.strip(), time.perf_counter()))

    async def handle_event(event: Any) -> None:
        if str(getattr(event, "type", "")) == "server.action.interaction_end":
            interaction_ended.set()

    async def handle_audio(message: Any) -> None:
        nonlocal audio_speech_started, audio_silence_ms
        if not message.audio_base64:
            return
        data = base64.b64decode(message.audio_base64)
        sample_rate = int(message.sample_rate or 8000)
        rms = _pcm_rms(data)
        duration_ms = len(data) / (2 * sample_rate) * 1000
        if rms > 20:
            if not audio_speech_started:
                audio_buffer.clear()
            audio_speech_started = True
            audio_silence_ms = 0.0
            audio_buffer.extend(data)
        elif audio_speech_started:
            audio_buffer.extend(data)
            audio_silence_ms += duration_ms
            if audio_silence_ms >= 800:
                captured = bytes(audio_buffer)
                audio_buffer.clear()
                audio_speech_started = False
                audio_silence_ms = 0.0
                await audio_turn_queue.put((captured, sample_rate, time.perf_counter()))

    async def handle_transcript(message: Any) -> None:
        # CALL sessions expose speech transcripts; only bot turns should wake
        # the scripted user because caller text was already supplied locally.
        role = str(getattr(message, "role", ""))
        content = str(getattr(message, "content", "")).strip()
        if role == "bot" and content:
            await text_queue.put((content, time.perf_counter()))
        elif role == "user" and content:
            # Streaming transcripts may repeat partial hypotheses; preserve
            # them for fidelity validation without treating them as new turns.
            observed_user_transcripts.append(content)

    variables = dict(scenario.visible_context)
    config = InteractionConfig(
        user_identifier_type=UserIdentifierType.CUSTOM,
        user_identifier=f"eval:{run_id}:{scenario.scenario_id}",
        org_id=settings.org_id,
        workspace_id=settings.workspace_id,
        app_id=settings.app_id,
        version=settings.app_version,
        interaction_type=interaction_type,
        sample_rate=16000,
        agent_variables=variables,
    )
    agent = TracingSamvaadAgent(
        api_key=SecretStr(settings.api_key),
        config=config,
        text_callback=handle_text,
        audio_callback=handle_audio,
        event_callback=handle_event,
        transcript_callback=handle_transcript,
    )
    environment = EMIEnvironment.from_initial(scenario.initial_environment)
    termination = "script_exhausted"
    model_wait_started = time.perf_counter()
    try:
        await agent.start()
        connected = await agent.wait_for_connect(timeout=15.0)
        if not connected:
            raise RuntimeError("Indus SDK did not connect within 15 seconds")
        # Capture the configured opening when the runtime emits one, but do not
        # fail the run if CHAT waits for the first user message.
        try:
            opening, received_at = await asyncio.wait_for(text_queue.get(), timeout=5.0)
            turns.append(ConversationTurn(len(turns) + 1, "agent", opening, round((received_at - model_wait_started) * 1000, 1)))
        except asyncio.TimeoutError:
            pass

        for step in scenario.user_steps[: scenario.max_agent_turns]:
            if interaction_ended.is_set():
                termination = "agent_terminal"
                break
            turns.append(ConversationTurn(len(turns) + 1, "caller", step.text))
            if interaction_type == InteractionType.CALL:
                pcm = synthesize_caller_pcm(step.text, scenario.language)
                audio_conditions = [item for item in scenario.perturbations if item != "barge_in_text_proxy"]
                await _stream_pcm(
                    agent,
                    apply_pcm_perturbations(pcm, audio_conditions, seed=23 + len(turns)),
                    sample_rate=16000,
                )
                # Latency begins at end-of-user-audio, matching perceived turn
                # latency rather than including the caller's speaking duration.
                sent_at = time.perf_counter()
            else:
                sent_at = time.perf_counter()
                await agent.send_text(step.text)
            try:
                if interaction_type == InteractionType.CALL:
                    _audio, _sample_rate, received_at = await asyncio.wait_for(audio_turn_queue.get(), timeout=response_timeout_seconds)
                    try:
                        response, transcript_at = await asyncio.wait_for(text_queue.get(), timeout=1.5)
                        received_at = max(received_at, transcript_at)
                    except asyncio.TimeoutError:
                        response = "[agent audio captured; bot transcript unavailable]"
                else:
                    response, received_at = await asyncio.wait_for(text_queue.get(), timeout=response_timeout_seconds)
            except asyncio.TimeoutError:
                termination = "response_timeout"
                break
            turns.append(ConversationTurn(len(turns) + 1, "agent", response, round((received_at - sent_at) * 1000, 1)))
            if interaction_ended.is_set():
                termination = "agent_terminal"
                break
    finally:
        await agent.stop()

    runtime_variables = _runtime_variables(agent.raw_messages)
    disposition = str(runtime_variables.get("disposition") or "call_disconnected")
    try:
        if disposition != "call_disconnected":
            environment.execute("record_disposition", {"disposition": disposition})
    except ToolExecutionError:
        pass
    tool_events = _runtime_tool_events(agent.raw_messages)
    consumed = sum(turn.actor == "caller" for turn in turns)
    run = ScenarioRun(
        schema_version="scenario-run.v1",
        run_id=run_id,
        scenario_id=scenario.scenario_id,
        candidate_id=f"indus-v{settings.app_version}",
        candidate_hash=hashlib.sha256(f"{settings.app_id}:v{settings.app_version}".encode()).hexdigest(),
        adapter=f"sarvam_conv_ai_sdk.{interaction_type.value}",
        started_at=started.isoformat(),
        ended_at=datetime.now(UTC).isoformat(),
        termination_reason=termination,
        interaction_id=agent.get_interaction_id(),
        turns=turns,
        tool_events=tool_events,
        initial_state=scenario.initial_environment,
        final_state={**environment.snapshot(), "runtime_variables": runtime_variables},
        agent_declared_disposition=disposition,
        simulator_validation={
            "passed": consumed > 0 and termination != "response_timeout",
            "consumed_steps": consumed,
            "available_steps": len(scenario.user_steps),
            "termination_was_explicit": termination == "agent_terminal",
        },
        provenance={
            "sdk": "sarvam-conv-ai-sdk==1.0.21",
            "interaction_type": interaction_type.value,
            "app_id": settings.app_id,
            "app_version": settings.app_version,
            "raw_message_count": len(agent.raw_messages),
            "raw_message_types": sorted({str(message.get("type")) for message in agent.raw_messages}),
            "observed_user_transcripts": observed_user_transcripts,
            "audio_perturbations": scenario.perturbations,
            "latency_semantics": "end_of_user_audio_to_completed_agent_audio",
        },
    )
    return run, _redact_raw_messages(agent.raw_messages)


async def run_suite(
    scenarios: list[EvaluationScenario],
    settings: Settings,
    output: Path,
    *,
    interaction_type: InteractionType = InteractionType.CHAT,
    adaptive_duplex: bool = False,
    caller_policy: AdaptiveCallerPolicy | None = None,
    speech_synthesizer: SpeechSynthesizer | None = None,
    live_budget: LiveBudgetLedger | None = None,
    provider_retries: int = 0,
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    partial_runs = output / "runs.partial.jsonl"
    partial_metrics = output / "metrics.partial.jsonl"
    partial_frames = output / "raw_frames.partial.jsonl"
    runs = [ScenarioRun.from_record(item) for item in read_jsonl(partial_runs)] if partial_runs.exists() else []
    metrics = read_jsonl(partial_metrics) if partial_metrics.exists() else []
    raw_frames = read_jsonl(partial_frames) if partial_frames.exists() else []
    completed_ids = {run.scenario_id for run in runs}
    for scenario in scenarios:
        if scenario.scenario_id in completed_ids:
            continue
        candidate_id = f"indus-v{settings.app_version}"
        reservation: LiveReservation | None = None
        if live_budget is None:
            raise RuntimeError("live Indus suite requires a LiveBudgetLedger")
        reservation = live_budget.reserve(
            scenario_id=scenario.scenario_id,
            candidate_id=candidate_id,
            interaction_type="adaptive_call" if adaptive_duplex else interaction_type.value,
        )
        last_error: Exception | None = None
        run: ScenarioRun | None = None
        raw: list[dict[str, Any]] = []
        for attempt in range(provider_retries + 1):
            try:
                if adaptive_duplex:
                    if interaction_type != InteractionType.CALL:
                        raise ValueError("adaptive duplex requires --interaction-type call")
                    if caller_policy is None or speech_synthesizer is None:
                        raise ValueError("adaptive duplex requires caller policy and speech synthesizer")
                    run, raw = await run_adaptive_indus_scenario(
                        scenario,
                        settings,
                        caller_policy=caller_policy,
                        speech_synthesizer=speech_synthesizer,
                        media_output=output / "media",
                    )
                else:
                    run, raw = await run_indus_scenario(scenario, settings, interaction_type=interaction_type)
                break
            except Exception as exc:  # provider transport retry; partial evidence is preserved
                last_error = exc
                if attempt < provider_retries:
                    # A provider retry is a separately budgeted paid attempt.
                    live_budget.finalize(
                        reservation,
                        status="failed",
                        error=f"{type(exc).__name__}: {exc}",
                    )
                    reservation = live_budget.reserve(
                        scenario_id=f"{scenario.scenario_id}:retry-{attempt + 1}",
                        candidate_id=candidate_id,
                        interaction_type="adaptive_call" if adaptive_duplex else interaction_type.value,
                    )
                    await asyncio.sleep(2.0)
        else:
            live_budget.finalize(
                reservation,
                status="failed",
                error=f"{type(last_error).__name__}: {last_error}",
            )
            write_json(
                output / "provider_error.json",
                {"scenario_id": scenario.scenario_id, "error_type": type(last_error).__name__, "message": str(last_error)},
            )
            raise RuntimeError(
                f"Indus scenario failed after {provider_retries + 1} paid attempt(s): {scenario.scenario_id}"
            ) from last_error
        if run is None:
            raise RuntimeError("provider returned without a ScenarioRun")
        live_budget.finalize(
            reservation,
            status="completed" if run.turns else "connected_empty",
            interaction_id=run.interaction_id,
        )
        runs.append(run)
        metrics.append(evaluate_run(scenario, run))
        raw_frames.append({"run_id": run.run_id, "scenario_id": scenario.scenario_id, "messages": raw})
        write_jsonl(partial_runs, [item.to_record() for item in runs])
        write_jsonl(partial_metrics, metrics)
        write_jsonl(partial_frames, raw_frames)
    summary = {
        "schema_version": "indus-chat-suite.v1",
        "candidate_id": f"indus-v{settings.app_version}",
        "adapter": (
            "sarvam-conv-ai-sdk==1.0.21/CALL_ADAPTIVE_DUPLEX"
            if adaptive_duplex
            else f"sarvam-conv-ai-sdk==1.0.21/{interaction_type.value.upper()}"
        ),
        "aggregate": aggregate(metrics),
        "scenario_count": len(scenarios),
        "interaction_ids": [run.interaction_id for run in runs],
        "claim_boundary": (
            "Live adaptive audio-in/audio-out Samvaad runtime with a local caller audio fixture and Gemini hidden-goal policy. "
            "Samvaad is the complete audio-native agent under test; no external STT/LLM/TTS reconstruction is scored. "
            "This exercises concurrent audio, interruption handling, tools and observed barge-in; matched human voice remains a separate gate."
            if adaptive_duplex
            else "Live Indus CALL runtime with locally synthesized PCM caller speech. This exercises VAD, STT, policy, and TTS, "
            "but synthetic-speaker fidelity must pass validation and this is not the final matched human voice result."
            if interaction_type == InteractionType.CALL
            else "Live Indus conversation engine in CHAT mode. This validates policy/runtime integration, not STT/TTS or voice experience."
        ),
        "paid_session_control": {
            "provider_retries": provider_retries,
            "ledger": str(live_budget.path),
        },
        "evaluator_freeze": (
            {
                "version": DUPLEX_EVALUATOR_VERSION,
                "bundle_sha256": json.loads(DEFAULT_DUPLEX_FREEZE.read_text(encoding="utf-8")).get("bundle_sha256"),
                "path": str(DEFAULT_DUPLEX_FREEZE),
            }
            if adaptive_duplex and DEFAULT_DUPLEX_FREEZE.exists()
            else {"version": DUPLEX_EVALUATOR_VERSION, "status": "freeze_missing"}
            if adaptive_duplex
            else None
        ),
    }
    write_jsonl(output / "runs.jsonl", [run.to_record() for run in runs])
    write_jsonl(output / "metrics.jsonl", metrics)
    write_jsonl(output / "raw_frames.jsonl", raw_frames)
    write_json(output / "summary.json", summary)
    partial_runs.unlink(missing_ok=True)
    partial_metrics.unlink(missing_ok=True)
    partial_frames.unlink(missing_ok=True)
    (output / "provider_error.json").unlink(missing_ok=True)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--scenario-id", action="append", default=[], help="Run only these exact scenario IDs")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--interaction-type", choices=["chat", "call"], default="chat")
    parser.add_argument("--adaptive-duplex", action="store_true")
    parser.add_argument("--caller-voice-provider", choices=["local", "sarvam"], default="local")
    parser.add_argument("--confirm-live", action="store_true")
    parser.add_argument("--max-live-sessions", type=int, default=1)
    parser.add_argument("--credit-budget", type=float, default=4.5)
    parser.add_argument("--estimated-credits-per-session", type=float, default=4.5)
    parser.add_argument("--allow-duplicate", action="store_true")
    parser.add_argument("--provider-retries", type=int, default=0)
    parser.add_argument("--live-ledger", type=Path)
    args = parser.parse_args()
    settings = Settings.from_environment(env_file=args.env_file)
    missing = settings.missing_fields(require_api_key=True)
    if missing:
        parser.error(f"missing environment values: {', '.join(missing)}")
    all_scenarios = load_scenarios(args.scenarios)
    if args.scenario_id:
        requested = set(args.scenario_id)
        scenarios = [scenario for scenario in all_scenarios if scenario.scenario_id in requested]
        missing_ids = sorted(requested - {scenario.scenario_id for scenario in scenarios})
        if missing_ids:
            parser.error(f"scenario IDs not found: {', '.join(missing_ids)}")
    else:
        scenarios = all_scenarios[: args.limit]
    interaction_type = InteractionType.CHAT if args.interaction_type == "chat" else InteractionType.CALL
    ledger = LiveBudgetLedger(
        args.live_ledger or args.output / "live_budget.json",
        max_sessions=args.max_live_sessions,
        credit_budget=args.credit_budget,
        estimated_credits_per_session=args.estimated_credits_per_session,
        confirmed_live=args.confirm_live,
        allow_duplicate=args.allow_duplicate,
    )
    policy: AdaptiveCallerPolicy | None = None
    synthesizer: SpeechSynthesizer | None = None
    if args.adaptive_duplex:
        load_env_file(Path(args.env_file))
        policy = GeminiAdaptiveCallerPolicy(
            cache_dir=ROOT / "artifacts" / "framework" / "cache" / "adaptive_caller"
        )
        synthesizer = LocalSpeechSynthesizer() if args.caller_voice_provider == "local" else SarvamSpeechSynthesizer()
    print(
        json.dumps(
            asyncio.run(
                run_suite(
                    scenarios,
                    settings,
                    args.output,
                    interaction_type=interaction_type,
                    adaptive_duplex=args.adaptive_duplex,
                    caller_policy=policy,
                    speech_synthesizer=synthesizer,
                    live_budget=ledger,
                    provider_retries=args.provider_retries,
                )
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
