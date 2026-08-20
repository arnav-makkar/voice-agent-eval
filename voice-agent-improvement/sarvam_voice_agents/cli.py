"""Safe CLI for previewing or executing one Instant Outbound call."""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any

from .client import SarvamAPIError, SarvamVoiceAgentsClient, build_outbound_payload
from .config import Settings


def _load_json_object(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _validate_run_id(run_id: str | None) -> str | None:
    """Validate a project-owned correlation identifier."""

    if run_id is None:
        return None
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", run_id):
        raise ValueError(
            "--run-id must be 1-128 characters using letters, numbers, ., _, or -"
        )
    return run_id


def _append_manifest(path: str, record: dict[str, Any]) -> None:
    manifest_path = Path(path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _masked_phone(value: str) -> str:
    if len(value) <= 6:
        return "***"
    return f"{value[:3]}{'*' * (len(value) - 7)}{value[-4:]}"


def _sanitized(payload: dict[str, Any]) -> dict[str, Any]:
    copy = deepcopy(payload)
    connection = copy["app_config"]["connection_config"]
    connection["agent_phone_number"] = _masked_phone(
        connection["agent_phone_number"]
    )
    user = copy["user_config"]
    user["user_phone_number"] = _masked_phone(user["user_phone_number"])
    return copy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preview or place one Sarvam Voice Agents outbound call."
    )
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--to-number", help="Overrides SARVAM_TEST_USER_PHONE_NUMBER")
    parser.add_argument("--variables", help="JSON object of per-call agent variables")
    parser.add_argument(
        "--run-id",
        help="Unique call correlation ID, for example BL-CTRL-01",
    )
    parser.add_argument(
        "--scenario-id",
        help="Frozen caller-card ID; defaults to the run ID",
    )
    parser.add_argument(
        "--manifest",
        default="manifests/calls.jsonl",
        help="Local JSONL index written after a successful executed call",
    )
    parser.add_argument("--initial-message")
    parser.add_argument("--initial-state")
    parser.add_argument("--webhook-url")
    parser.add_argument("--webhook-metadata", help="JSON object for webhook metadata")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually place the call. Without this flag, only a preview is printed.",
    )
    parser.add_argument(
        "--confirm-call",
        action="store_true",
        help="Required with --execute to acknowledge the external phone call.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.execute and not args.confirm_call:
        parser.error("--execute also requires --confirm-call")
    if args.execute and not args.run_id:
        parser.error("--execute also requires a unique --run-id")

    try:
        settings = Settings.from_environment(
            env_file=args.env_file,
            user_phone_number=args.to_number,
        )
        missing = settings.missing_fields(require_api_key=args.execute)
        if missing:
            parser.error("Missing configuration: " + ", ".join(missing))

        run_id = _validate_run_id(args.run_id)
        agent_variables = _load_json_object(args.variables)
        if agent_variables and "run_id" in agent_variables:
            raise ValueError(
                "run_id is local experiment metadata; remove it from agent variables"
            )
        payload = build_outbound_payload(
            settings,
            agent_variables=agent_variables,
            initial_bot_message=args.initial_message,
            initial_state_name=args.initial_state,
            webhook_url=args.webhook_url,
            webhook_metadata=_load_json_object(args.webhook_metadata),
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    if not args.execute:
        print("DRY RUN — no call was placed")
        print(json.dumps(_sanitized(payload), indent=2, ensure_ascii=False))
        return 0

    client = SarvamVoiceAgentsClient(
        api_key=settings.api_key,
        org_id=settings.org_id,
        workspace_id=settings.workspace_id,
    )
    try:
        attempt_id = client.create_outbound_call(payload)
    except SarvamAPIError as exc:
        print(f"Call request failed: {exc}", file=sys.stderr)
        return 1

    manifest_record = {
        "run_id": run_id,
        "scenario_id": args.scenario_id or run_id,
        "attempt_id": attempt_id,
        "app_id": settings.app_id,
        "app_version": settings.app_version,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    _append_manifest(args.manifest, manifest_record)
    print(
        json.dumps(
            {
                "attempt_id": attempt_id,
                "run_id": run_id,
                "manifest": args.manifest,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
