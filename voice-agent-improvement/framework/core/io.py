"""Atomic artifact I/O with content-addressed manifests."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from .schemas import canonical_json


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(records)
    body = "".join(canonical_json(row) + "\n" for row in rows)
    _atomic_text(path, body)
    return {
        "path": str(path),
        "records": len(rows),
        "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "bytes": len(body.encode("utf-8")),
    }


def write_json(path: Path, value: Any) -> dict[str, Any]:
    body = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    _atomic_text(path, body)
    return {
        "path": str(path),
        "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "bytes": len(body.encode("utf-8")),
    }


def write_text(path: Path, text: str) -> dict[str, Any]:
    body = text if text.endswith("\n") else text + "\n"
    _atomic_text(path, body)
    return {
        "path": str(path),
        "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "bytes": len(body.encode("utf-8")),
    }


def manifest(stage: str, artifacts: list[dict[str, Any]], **metadata: Any) -> dict[str, Any]:
    return {
        "schema_version": "framework-manifest.v1",
        "stage": stage,
        "created_at": datetime.now(UTC).isoformat(),
        "artifacts": artifacts,
        "metadata": metadata,
    }
