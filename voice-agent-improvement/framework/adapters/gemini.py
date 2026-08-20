"""Small Gemini structured-output adapter with auditable local caching."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from framework.core.io import write_json
from framework.core.schemas import canonical_json


DEFAULT_MODEL = "gemini-3.6-flash"
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def load_env_file(path: Path) -> None:
    """Load missing names from a local dotenv file without logging values."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class GeminiResult:
    data: dict[str, Any]
    metadata: dict[str, Any]


class GeminiJsonClient:
    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
        cache_dir: Path | None = None,
        timeout_seconds: float = 180,
        max_retries: int = 3,
        session: requests.Session | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        self.cache_dir = cache_dir
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.session = session or requests.Session()

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        response_schema: dict[str, Any],
        temperature: float = 0.2,
        thinking_level: str = "high",
        cache_namespace: str = "default",
        use_cache: bool = True,
    ) -> GeminiResult:
        request_body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
                "responseJsonSchema": response_schema,
                "thinkingConfig": {"thinkingLevel": thinking_level},
            },
        }
        return self._complete_request(
            request_body=request_body,
            adapter_version="gemini-json.v1",
            cache_namespace=cache_namespace,
            use_cache=use_cache,
        )

    def complete_audio_json(
        self,
        *,
        system: str,
        user: str,
        audio_wav: bytes,
        response_schema: dict[str, Any],
        temperature: float = 0.2,
        thinking_level: str = "high",
        cache_namespace: str = "audio",
        use_cache: bool = False,
    ) -> GeminiResult:
        """Return structured JSON after directly hearing an inline WAV.

        This is used by the *caller simulator*, never as a replacement for the
        audio-native agent under test. Audio is not cached by default. Cache
        records, when explicitly enabled, contain only the structured response
        and hashes—not the input WAV or API key.
        """
        if not audio_wav:
            raise ValueError("audio_wav must not be empty")
        audio_sha256 = hashlib.sha256(audio_wav).hexdigest()
        request_body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": user},
                        {
                            "inlineData": {
                                "mimeType": "audio/wav",
                                "data": base64.b64encode(audio_wav).decode("ascii"),
                            }
                        },
                    ],
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
                "responseJsonSchema": response_schema,
                "thinkingConfig": {"thinkingLevel": thinking_level},
            },
        }
        return self._complete_request(
            request_body=request_body,
            adapter_version="gemini-audio-json.v1",
            cache_namespace=cache_namespace,
            use_cache=use_cache,
            input_metadata={"audio_sha256": audio_sha256, "audio_bytes": len(audio_wav)},
        )

    def _complete_request(
        self,
        *,
        request_body: dict[str, Any],
        adapter_version: str,
        cache_namespace: str,
        use_cache: bool,
        input_metadata: dict[str, Any] | None = None,
    ) -> GeminiResult:
        request_fingerprint = {
            "adapter_version": adapter_version,
            "model": self.model,
            "cache_namespace": cache_namespace,
            "request": request_body,
        }
        request_hash = hashlib.sha256(canonical_json(request_fingerprint).encode("utf-8")).hexdigest()
        cache_path = self.cache_dir / cache_namespace / f"{request_hash}.json" if self.cache_dir else None
        if use_cache and cache_path and cache_path.exists():
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            cached["metadata"]["cache_hit"] = True
            return GeminiResult(data=cached["data"], metadata=cached["metadata"])

        started = time.perf_counter()
        last_error: requests.RequestException | None = None
        response = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.post(
                    f"{BASE_URL}/{self.model}:generateContent",
                    headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                    json=request_body,
                    timeout=self.timeout_seconds,
                )
                break
            except requests.RequestException as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    raise RuntimeError(f"Gemini request failed after {attempt + 1} attempts: {exc}") from exc
                time.sleep(min(2**attempt, 8))
        if response is None:
            raise RuntimeError(f"Gemini request failed: {last_error}")
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        if not response.ok:
            raise RuntimeError(f"Gemini returned HTTP {response.status_code}: {response.text[:800]}")
        envelope = response.json()
        try:
            text = envelope["candidates"][0]["content"]["parts"][0]["text"]
            data = json.loads(text)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Gemini did not return valid structured JSON: {exc}") from exc

        metadata = {
            "adapter_version": adapter_version,
            "model_requested": self.model,
            "model_version": envelope.get("modelVersion", self.model),
            "request_hash": request_hash,
            "response_hash": hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest(),
            "usage": envelope.get("usageMetadata", {}),
            "latency_ms": latency_ms,
            "cache_hit": False,
            **(input_metadata or {}),
        }
        if cache_path:
            write_json(cache_path, {"data": data, "metadata": metadata})
        return GeminiResult(data=data, metadata=metadata)
