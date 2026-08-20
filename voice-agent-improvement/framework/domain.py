"""Domain-pack registry used by ingestion, generation, evaluation, and release."""

from __future__ import annotations

from pathlib import Path
import json

from .core.schemas import DomainPack


PACKS = Path(__file__).with_name("domain_packs")


def load_domain_pack(domain_id: str) -> DomainPack:
    candidates = {
        json.loads(path.read_text(encoding="utf-8"))["domain_id"]: path
        for path in PACKS.glob("*.json")
    }
    if domain_id not in candidates:
        raise KeyError(f"unknown domain pack {domain_id!r}; available: {', '.join(sorted(candidates))}")
    return DomainPack.from_path(candidates[domain_id])


def list_domain_packs() -> list[str]:
    return sorted(
        json.loads(path.read_text(encoding="utf-8"))["domain_id"]
        for path in PACKS.glob("*.json")
    )
