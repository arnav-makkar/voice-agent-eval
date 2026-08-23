"""Sarvam Samvaad assistant-server integration for EVA.

This project-owned adapter keeps the deployed Indus/Samvaad agent as the
complete system under test.  EVA's realtime caller connects using Twilio media
frames; the adapter converts and forwards that audio into Samvaad's official
bidirectional CALL runtime, then returns Shubh's live audio to the caller.

It intentionally does not reconstruct Shubh with a separate STT/LLM/TTS stack.
"""

from __future__ import annotations

import asyncio
import audioop
import base64
import copy
import json
import math
import os
import random
import struct
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import certifi
import httpx
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import SecretStr
from sarvam_conv_ai_sdk import AsyncSamvaadAgent, InteractionConfig, InteractionType
from sarvam_conv_ai_sdk.messages.types import MsgStatus, UserIdentifierType

from eva.assistant.base_server import AbstractAssistantServer
from eva.assistant.pipeline.observers import FrameworkLogWriter, MetricsLogWriter
from eva.utils.audio_utils import (
    create_twilio_media_message,
    mulaw_8k_to_pcm16_16k,
    parse_twilio_media_message,
    resample_pcm16_soxr,
    sync_buffer_to_position,
)
from eva.utils.logging import get_logger

logger = get_logger(__name__)

SAMVAAD_SAMPLE_RATE = 16_000
MULAW_SAMPLE_RATE = 8_000
MULAW_CHUNK_BYTES = 160
MULAW_CHUNK_DURATION_SECONDS = 0.02
SPEECH_RMS_THRESHOLD = 20
ANALYTICS_BASE_URL = "https://apps.sarvam.ai/api/analytics/v1"


def _wall_ms() -> str:
    return str(int(round(time.time() * 1000)))


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


def _pcm16_to_mulaw_8k(pcm: bytes, source_rate: int) -> bytes:
    pcm_8k = resample_pcm16_soxr(pcm, source_rate, MULAW_SAMPLE_RATE)
    return audioop.lin2ulaw(pcm_8k, 2)


def _redact_frame(message: dict[str, Any]) -> dict[str, Any]:
    item = copy.deepcopy(message)
    encoded = item.pop("audio_base64", None)
    if encoded:
        try:
            item["audio_bytes"] = len(base64.b64decode(str(encoded)))
        except Exception:
            item["audio_bytes"] = None
        item["audio_redacted"] = True
    return item


def _runtime_variables_from_attempt(
    attempt: dict[str, Any],
    initial_variables: dict[str, Any],
) -> dict[str, Any]:
    """Return values changed or populated by the completed Indus runtime."""
    variables = attempt.get("agent_variables")
    if not isinstance(variables, dict):
        return {}
    return {
        key: value
        for key, value in variables.items()
        if key not in initial_variables or value != initial_variables.get(key)
    }


def _meaningful_runtime_value(value: Any) -> bool:
    """Exclude provider sentinels that mean an output was not populated."""
    return value is not None and str(value).strip().lower() not in {"", "na", "n/a", "none", "null"}


class TracingSamvaadAgent(AsyncSamvaadAgent):
    """Retain provider frames before the pinned SDK performs typed routing."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.raw_messages: list[dict[str, Any]] = []
        self.interaction_ended = asyncio.Event()

    async def _route_message(self, message: dict[str, Any]) -> None:  # noqa: SLF001
        self.raw_messages.append(copy.deepcopy(message))
        if message.get("type") == "server.action.interaction_end":
            self.interaction_ended.set()
        await super()._route_message(message)


class SamvaadAssistantServer(AbstractAssistantServer):
    """EVA assistant server backed by a deployed Sarvam Samvaad agent."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._audio_sample_rate = SAMVAAD_SAMPLE_RATE
        params = self.pipeline_config.s2s_params or {}
        self._model = str(params.get("model", "sarvam-samvaad"))
        self._api_key = str(params.get("api_key") or os.getenv("SARVAM_VOICE_AGENTS_API_KEY") or "")
        self._org_id = str(params.get("org_id") or os.getenv("SARVAM_ORG_ID") or "")
        self._workspace_id = str(params.get("workspace_id") or os.getenv("SARVAM_WORKSPACE_ID") or "")
        self._app_id = str(params.get("app_id") or os.getenv("SARVAM_APP_ID") or "")
        self._app_version = int(params.get("app_version") or os.getenv("SARVAM_APP_VERSION") or 1)
        missing = [
            name
            for name, value in {
                "api_key": self._api_key,
                "org_id": self._org_id,
                "workspace_id": self._workspace_id,
                "app_id": self._app_id,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(f"Missing Samvaad configuration: {', '.join(missing)}")

        with open(self.scenario_db_path, encoding="utf-8") as handle:
            scenario_db = json.load(handle)
        self._agent_variables = dict(scenario_db.get("agent_variables") or {})
        self._evaluation_config = dict(scenario_db.get("evaluation") or {})
        self._audio_perturbation = dict(scenario_db.get("audio_perturbation") or {})
        self._perturbation_rng = random.Random(int(self._audio_perturbation.get("seed", 0)))
        self._perturbation_chunks = 0
        self._perturbation_dropped = 0
        self._tool_base_url = str(os.getenv("LOOPLINE_TOOL_BASE_URL") or "").rstrip("/")
        self._tool_secret = str(os.getenv("LOOPLINE_TOOL_SECRET") or "")
        self._tool_run_id = self.conversation_id
        self._tool_account_id = str(
            self._evaluation_config.get("account_id")
            or self._agent_variables.get("transactionReference")
            or ""
        )
        self._stream_sid = self.conversation_id
        self._samvaad_agent: TracingSamvaadAgent | None = None
        self._session_done = asyncio.Event()
        self._conversation_ending = False
        self._user_speaking = False
        self._assistant_speaking = False
        self._user_speech_start_ms: str | None = None
        self._user_speech_stop_ms: str | None = None
        self._assistant_first_audio_ms: str | None = None
        self._latest_user_transcript = ""
        self._flushed_user_transcript = ""
        self._latest_bot_transcript = ""
        self._flushed_bot_transcript = ""
        self._transport_events: list[dict[str, Any]] = []
        self._saved_raw_messages: list[dict[str, Any]] = []
        self._interaction_id: str | None = None
        self._provider_completed = False
        self._session_started_at = datetime.now(UTC)

    def _trace(self, event: str, **details: Any) -> None:
        self._transport_events.append({"event": event, "timestamp_ms": _wall_ms(), **details})

    def _perturb_user_mulaw(self, mulaw: bytes) -> tuple[bytes, float]:
        """Apply one deterministic τ-Voice-inspired caller-audio condition."""
        self._perturbation_chunks += 1
        kind = str(self._audio_perturbation.get("kind") or "clean")
        if kind == "packet_loss":
            probability = float(self._audio_perturbation.get("probability", 0.0))
            if self._perturbation_rng.random() < probability:
                self._perturbation_dropped += 1
                return b"\xff" * len(mulaw), 0.0
            return mulaw, 0.0
        if kind == "low_gain":
            pcm = audioop.ulaw2lin(mulaw, 2)
            return audioop.lin2ulaw(audioop.mul(pcm, 2, float(self._audio_perturbation.get("gain", 1.0))), 2), 0.0
        if kind == "background_noise":
            pcm = audioop.ulaw2lin(mulaw, 2)
            signal_rms = max(1, audioop.rms(pcm, 2))
            snr_db = float(self._audio_perturbation.get("snr_db", 15.0))
            noise_rms = max(1.0, signal_rms / math.pow(10.0, snr_db / 20.0))
            samples = []
            for (sample,) in struct.iter_unpack("<h", pcm):
                noisy = int(sample + self._perturbation_rng.gauss(0.0, noise_rms))
                samples.append(max(-32768, min(32767, noisy)))
            noisy_pcm = struct.pack(f"<{len(samples)}h", *samples)
            return audioop.lin2ulaw(noisy_pcm, 2), 0.0
        if kind == "jitter":
            # Delay a minority of frames rather than every 20 ms frame, which
            # creates realistic burst jitter without stretching the call 4x.
            delay = 0.0
            if self._perturbation_rng.random() < 0.12:
                delay = self._perturbation_rng.uniform(0.0, float(self._audio_perturbation.get("max_delay_ms", 0.0))) / 1000.0
            return mulaw, delay
        return mulaw, 0.0

    async def _seed_tool_run(self) -> None:
        if not self._tool_base_url or not self._tool_secret or not self._tool_account_id:
            self._trace("tool_state_not_configured")
            return
        payload = {
            "run_id": self._tool_run_id,
            "account_id": self._tool_account_id,
            "outstanding_amount": str(self._agent_variables.get("outstandingAmount") or "0"),
            "payment_status": "unpaid",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self._tool_base_url}/v1/evaluation/runs",
                headers={"X-Loopline-Tool-Key": self._tool_secret},
                json=payload,
            )
        if response.status_code not in {200, 409}:
            response.raise_for_status()
        self._trace("tool_state_seeded", run_id=self._tool_run_id, account_id=self._tool_account_id)

    async def _fetch_tool_run(self) -> dict[str, Any] | None:
        if not self._tool_base_url or not self._tool_secret:
            return None
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self._tool_base_url}/v1/evaluation/runs/{self._tool_run_id}",
                    headers={"X-Loopline-Tool-Key": self._tool_secret},
                )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            self._trace("tool_state_fetch_error", detail=str(exc))
            return None

    async def start(self) -> None:
        if self._running:
            return
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._fw_log = FrameworkLogWriter(self.output_dir)
        self._metrics_log = MetricsLogWriter(self.output_dir)
        self._app = FastAPI()

        @self._app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket) -> None:
            await websocket.accept()
            await self._handle_session(websocket)

        @self._app.websocket("/")
        async def websocket_root(websocket: WebSocket) -> None:
            await websocket.accept()
            await self._handle_session(websocket)

        self._server = uvicorn.Server(
            uvicorn.Config(self._app, host="0.0.0.0", port=self.port, log_level="warning", lifespan="off")
        )
        self._running = True
        self._server_task = asyncio.create_task(self._server.serve())
        while not self._server.started:
            await asyncio.sleep(0.01)
        logger.info(f"Samvaad EVA bridge started on ws://localhost:{self.port}/ws")

    def notify_conversation_ending(self, reason: str | None = None) -> None:
        self._conversation_ending = True
        self._trace("conversation_ending", reason=reason)
        self._session_done.set()

    async def _shutdown(self) -> None:
        if self._samvaad_agent is not None:
            try:
                await self._samvaad_agent.stop()
            except Exception as exc:
                logger.warning(f"Samvaad stop failed during shutdown: {exc}")
            self._samvaad_agent = None
        if not self._running:
            return
        self._running = False
        self._session_done.set()
        if self._server:
            self._server.should_exit = True
        if self._server_task:
            try:
                await asyncio.wait_for(self._server_task, timeout=5.0)
            except TimeoutError:
                self._server_task.cancel()
                try:
                    await self._server_task
                except asyncio.CancelledError:
                    pass
        self._server = None
        self._server_task = None

    def _flush_user_transcript(self) -> None:
        current = self._latest_user_transcript.strip()
        if not current or current == self._flushed_user_transcript:
            return
        previous = self._flushed_user_transcript
        delta = current[len(previous) :].strip() if previous and current.startswith(previous) else current
        if delta:
            self.audit_log.append_user_input(delta, timestamp_ms=self._user_speech_start_ms or _wall_ms())
        self._flushed_user_transcript = current

    def _flush_bot_transcript(self) -> None:
        current = self._latest_bot_transcript.strip()
        if not current or current == self._flushed_bot_transcript:
            return
        self._flush_user_transcript()
        self.audit_log.append_assistant_output(
            current,
            timestamp_ms=self._assistant_first_audio_ms or _wall_ms(),
        )
        if self._fw_log:
            self._fw_log.llm_response(current)
            self._fw_log.s2s_transcript(current, timestamp_ms=int(self._assistant_first_audio_ms or _wall_ms()))
            self._fw_log.turn_end(was_interrupted=False)
        self._flushed_bot_transcript = current

    async def _handle_session(self, websocket: WebSocket) -> None:
        self._stream_sid = self.conversation_id
        self._session_done.clear()
        output_queue: asyncio.Queue[bytes] = asyncio.Queue()

        async def on_event(event: Any) -> None:
            event_type = str(getattr(event, "type", ""))
            interaction_id = getattr(event, "interaction_id", None)
            if interaction_id:
                self._interaction_id = str(interaction_id)
            self._trace("samvaad_event", type=event_type, interaction_id=interaction_id)
            if event_type == "server.action.interaction_end":
                self._provider_completed = True
                self._session_done.set()

        async def on_transcript(message: Any) -> None:
            role = str(getattr(message, "role", ""))
            text = str(getattr(message, "content", "")).strip()
            if not text:
                return
            self._trace("samvaad_transcript", role=role, text=text)
            if role == "user":
                self._latest_user_transcript = text
            elif role == "bot":
                self._latest_bot_transcript = text

        async def on_audio(message: Any) -> None:
            encoded = str(getattr(message, "audio_base64", "") or "")
            status = getattr(message, "status", None)
            if encoded:
                pcm = base64.b64decode(encoded)
                source_rate = int(getattr(message, "sample_rate", None) or MULAW_SAMPLE_RATE)
                pcm_16k = resample_pcm16_soxr(pcm, source_rate, SAMVAAD_SAMPLE_RATE)
                speech = audioop.rms(pcm_16k, 2) > SPEECH_RMS_THRESHOLD if pcm_16k else False
                if speech and not self._assistant_speaking:
                    self._assistant_speaking = True
                    self._assistant_first_audio_ms = _wall_ms()
                    if self._fw_log:
                        self._fw_log.turn_start(timestamp_ms=int(self._assistant_first_audio_ms))
                    if self._user_speech_stop_ms and self._metrics_log:
                        latency_ms = int(self._assistant_first_audio_ms) - int(self._user_speech_stop_ms)
                        if 0 < latency_ms < 30_000:
                            self._metrics_log.write_latency("model_response", latency_ms / 1000, self._model)
                            self._trace("model_response_latency", latency_ms=latency_ms)
                    self._user_speech_stop_ms = None
                    self._trace("assistant_audio_start", sample_rate=source_rate)
                if not self._user_speaking:
                    sync_buffer_to_position(self.user_audio_buffer, len(self.assistant_audio_buffer))
                self.assistant_audio_buffer.extend(pcm_16k)
                # Samvaad can emit continuous silence between responses. Do
                # not forward that as assistant media: EVA would otherwise see
                # one 60-second assistant turn and collapse all turn boundaries.
                if speech or self._assistant_speaking:
                    mulaw = _pcm16_to_mulaw_8k(pcm, source_rate)
                    for offset in range(0, len(mulaw), MULAW_CHUNK_BYTES):
                        chunk = mulaw[offset : offset + MULAW_CHUNK_BYTES]
                        if len(chunk) < MULAW_CHUNK_BYTES:
                            chunk += b"\xff" * (MULAW_CHUNK_BYTES - len(chunk))
                        await output_queue.put(chunk)
            if status == MsgStatus.COMPLETED:
                if self._assistant_speaking:
                    self._trace("assistant_audio_end")
                self._assistant_speaking = False
                self._flush_bot_transcript()

        provider_variables = dict(self._agent_variables)
        # Indus v15 uses snake_case for the two runtime date inputs because
        # newly-created variable names cannot contain uppercase characters.
        # Keep the frozen scenario contract unchanged and add provider aliases
        # only for the committed release candidate.
        if self._app_version >= 15:
            provider_variables["current_date"] = str(provider_variables.get("currentDate") or "")
            provider_variables["tomorrow_date"] = str(provider_variables.get("tomorrowDate") or "")
        # Existing Indus variables are reused as evaluation correlation fields
        # so the API-tool body can reference them without adding hidden values.
        provider_variables["campaignId"] = self._tool_run_id
        provider_variables["transactionReference"] = self._tool_account_id
        config = InteractionConfig(
            user_identifier_type=UserIdentifierType.CUSTOM,
            user_identifier=f"eva:{self.conversation_id}",
            org_id=self._org_id,
            workspace_id=self._workspace_id,
            app_id=self._app_id,
            version=self._app_version,
            interaction_type=InteractionType.CALL,
            sample_rate=SAMVAAD_SAMPLE_RATE,
            agent_variables=provider_variables,
        )
        os.environ.setdefault("SSL_CERT_FILE", certifi.where())
        agent = TracingSamvaadAgent(
            api_key=SecretStr(self._api_key),
            config=config,
            audio_callback=on_audio,
            event_callback=on_event,
            transcript_callback=on_transcript,
        )
        self._samvaad_agent = agent

        user_input_queue: asyncio.Queue[bytes] = asyncio.Queue()
        # 20 ms of PCM16 mono silence at 16 kHz, matching one telephony frame.
        USER_SILENCE_FRAME = b"\x00" * 640

        async def forward_user_audio() -> None:
            try:
                while self._running and not self._conversation_ending:
                    raw = await websocket.receive_text()
                    message = json.loads(raw)
                    event = message.get("event")
                    if event == "start":
                        self._stream_sid = message.get("start", {}).get("streamSid", self.conversation_id)
                        self._trace("twilio_start", stream_sid=self._stream_sid)
                    elif event == "stop":
                        self._trace("twilio_stop")
                        self._session_done.set()
                        break
                    elif event == "user_speech_start":
                        self._user_speaking = True
                        self._user_speech_start_ms = str(message.get("timestamp_ms") or _wall_ms())
                        self._trace("user_audio_start", source_timestamp_ms=self._user_speech_start_ms)
                    elif event == "user_speech_stop":
                        self._user_speaking = False
                        self._user_speech_stop_ms = str(message.get("timestamp_ms") or _wall_ms())
                        self._trace("user_audio_stop", source_timestamp_ms=self._user_speech_stop_ms)
                    elif event == "media":
                        mulaw = parse_twilio_media_message(raw)
                        if mulaw is None:
                            continue
                        mulaw, perturbation_delay = self._perturb_user_mulaw(mulaw)
                        if perturbation_delay:
                            await asyncio.sleep(perturbation_delay)
                        pcm_16k = mulaw_8k_to_pcm16_16k(mulaw)
                        if not self._assistant_speaking:
                            sync_buffer_to_position(self.assistant_audio_buffer, len(self.user_audio_buffer))
                        self.user_audio_buffer.extend(pcm_16k)
                        user_input_queue.put_nowait(pcm_16k)
            except WebSocketDisconnect:
                self._trace("twilio_disconnect")
                self._session_done.set()
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                if self._provider_completed or agent.interaction_ended.is_set() or self._session_done.is_set():
                    self._provider_completed = self._provider_completed or agent.interaction_ended.is_set()
                    self._trace("user_audio_after_provider_end", detail=str(exc))
                    self._session_done.set()
                    return
                raise

        async def pace_user_audio() -> None:
            """Send Samvaad an unbroken 20 ms caller stream.

            ElevenLabs only emits media while it is actually speaking. A real
            phone line carries silence between utterances, and Samvaad ends a
            turn by hearing that silence. With no packets at all the endpointer
            never fires, so the ASR keeps extending one segment and every
            transcript arrives with all prior turns still prepended.
            """
            next_send = time.monotonic()
            while self._running and not self._conversation_ending:
                try:
                    frame = user_input_queue.get_nowait()
                except asyncio.QueueEmpty:
                    frame = USER_SILENCE_FRAME
                try:
                    await agent.send_audio(frame)
                except Exception:
                    if self._session_done.is_set() or agent.interaction_ended.is_set():
                        return
                    raise
                next_send += MULAW_CHUNK_DURATION_SECONDS
                delay = next_send - time.monotonic()
                if delay > 0:
                    await asyncio.sleep(delay)
                else:
                    next_send = time.monotonic()

        async def pace_assistant_audio() -> None:
            next_send = time.monotonic()
            try:
                while self._running and not self._conversation_ending:
                    try:
                        chunk = await asyncio.wait_for(output_queue.get(), timeout=1.0)
                    except TimeoutError:
                        continue
                    await websocket.send_text(create_twilio_media_message(self._stream_sid, chunk))
                    now = time.monotonic()
                    if next_send <= now:
                        next_send = now
                    next_send += MULAW_CHUNK_DURATION_SECONDS
                    delay = next_send - time.monotonic()
                    if delay > 0:
                        await asyncio.sleep(delay)
            except (WebSocketDisconnect, asyncio.CancelledError):
                pass

        try:
            await self._seed_tool_run()
            await agent.start()
            if not await agent.wait_for_connect(timeout=15.0):
                raise RuntimeError("Samvaad did not connect within 15 seconds")
            self._interaction_id = agent.get_interaction_id()
            self._trace("samvaad_connected", interaction_id=self._interaction_id)
            forward_task = asyncio.create_task(forward_user_audio())
            user_pacer_task = asyncio.create_task(pace_user_audio())
            pacer_task = asyncio.create_task(pace_assistant_audio())
            done_task = asyncio.create_task(self._session_done.wait())
            provider_end_task = asyncio.create_task(agent.interaction_ended.wait())
            done, pending = await asyncio.wait(
                {forward_task, user_pacer_task, pacer_task, done_task, provider_end_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if provider_end_task in done or agent.interaction_ended.is_set():
                self._provider_completed = True
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            if self._provider_completed:
                try:
                    await websocket.send_text(
                        json.dumps({"event": "stop", "reason": "assistant_completed"})
                    )
                    self._trace("twilio_stop_sent", reason="assistant_completed")
                except Exception as exc:
                    self._trace("twilio_stop_send_failed", detail=str(exc))
            for task in done:
                if not task.cancelled() and task.exception():
                    raise task.exception()
        finally:
            self._flush_user_transcript()
            self._flush_bot_transcript()
            await agent.stop()
            self._interaction_id = agent.get_interaction_id() or self._interaction_id
            self._saved_raw_messages = copy.deepcopy(agent.raw_messages)
            self._samvaad_agent = None
            self._trace("samvaad_disconnected", interaction_id=self._interaction_id)

    async def _fetch_analytics_attempt(self) -> dict[str, Any] | None:
        """Fetch the authoritative completed attempt for output variables."""
        if not self._interaction_id:
            return None
        url = f"{ANALYTICS_BASE_URL}/{self._org_id}/{self._workspace_id}/{self._app_id}/attempts"
        params = {
            "start_datetime": (self._session_started_at - timedelta(minutes=5)).isoformat(),
            "end_datetime": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
            "limit": 100,
            "offset": 0,
            "sort_by": "start_datetime",
            "sort_order": "desc",
        }
        for attempt_index in range(6):
            try:
                async with httpx.AsyncClient(verify=certifi.where(), timeout=15.0) as client:
                    response = await client.get(
                        url,
                        headers={"X-API-Key": self._api_key},
                        params=params,
                    )
                    response.raise_for_status()
                    items = response.json().get("items", [])
                for item in items:
                    if isinstance(item, dict) and item.get("interaction_id") == self._interaction_id:
                        return item
            except Exception as exc:
                self._trace("analytics_fetch_error", attempt=attempt_index + 1, detail=str(exc))
            if attempt_index < 5:
                await asyncio.sleep(5.0)
        return None

    async def save_outputs(self) -> None:
        runtime_variables: dict[str, Any] = {}
        tool_events: list[dict[str, Any]] = []
        raw_messages = self._samvaad_agent.raw_messages if self._samvaad_agent else self._saved_raw_messages
        for message in raw_messages:
            if message.get("type") == "server.event.variable_update":
                update = (
                    _find_value(message, "variables")
                    or _find_value(message, "agent_variables")
                    or _find_value(message, "updates")
                )
                if isinstance(update, dict):
                    runtime_variables.update(update)
            elif message.get("type") == "server.event.tool_call":
                tool_events.append(_redact_frame(message))
        analytics_attempt = await self._fetch_analytics_attempt()
        if analytics_attempt:
            runtime_variables.update(_runtime_variables_from_attempt(analytics_attempt, self._agent_variables))
            redacted_attempt = {
                key: value
                for key, value in analytics_attempt.items()
                if key not in {"audio_url", "user_contact", "user_contact_hashed", "user_identifier"}
            }
            redacted_attempt["recording_available"] = bool(analytics_attempt.get("audio_url"))
            with open(self.output_dir / "samvaad_attempt.json", "w", encoding="utf-8") as handle:
                json.dump(redacted_attempt, handle, indent=2, ensure_ascii=False, default=str)
            self._trace("analytics_attempt_resolved", interaction_id=self._interaction_id)
        else:
            self._trace("analytics_attempt_not_found", interaction_id=self._interaction_id)
        # Project the provider's observable outcome onto the deterministic EMI
        # scenario state. Dynamic IDs and raw frames stay in sidecar artifacts
        # so EVA's expected-state comparison remains stable and meaningful.
        customer = self.tool_handler.db.setdefault("customer", {})
        disposition = runtime_variables.get("disposition")
        if disposition:
            customer["outcome"] = disposition
        if _meaningful_runtime_value(runtime_variables.get("promisedToPayDate")):
            customer["promise_to_pay_date"] = runtime_variables["promisedToPayDate"]
        if _meaningful_runtime_value(runtime_variables.get("callbackDateTime")):
            customer["callback_at"] = runtime_variables["callbackDateTime"]
        tool_run = await self._fetch_tool_run()
        if tool_run:
            tool_state = dict(tool_run.get("state") or {})
            if tool_state.get("promise_to_pay_date"):
                customer["promise_to_pay_date"] = tool_state["promise_to_pay_date"]
            if tool_state.get("callback"):
                customer["callback_at"] = tool_state["callback"]
            if tool_state.get("disposition"):
                customer["outcome"] = tool_state["disposition"]
            with open(self.output_dir / "loopline_tool_state.json", "w", encoding="utf-8") as handle:
                json.dump(tool_run, handle, indent=2, ensure_ascii=False, default=str)
            self._trace("tool_state_resolved", event_count=len(tool_run.get("events") or []))
        with open(self.output_dir / "samvaad_runtime.json", "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "interaction_id": self._interaction_id,
                    "variables": runtime_variables,
                    "tool_events": tool_events,
                },
                handle,
                indent=2,
                ensure_ascii=False,
                default=str,
            )
        events_path = self.output_dir / "samvaad_events.jsonl"
        with open(events_path, "w", encoding="utf-8") as handle:
            for message in raw_messages:
                handle.write(json.dumps(_redact_frame(message), ensure_ascii=False, default=str) + "\n")
        with open(self.output_dir / "samvaad_transport.json", "w", encoding="utf-8") as handle:
            self._trace(
                "audio_perturbation_summary",
                config=self._audio_perturbation or {"kind": "clean"},
                chunks=self._perturbation_chunks,
                dropped_chunks=self._perturbation_dropped,
            )
            json.dump(self._transport_events, handle, indent=2, ensure_ascii=False)
        await super().save_outputs()
