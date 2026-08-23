"""Run exactly one guarded EVA live-audio conversation against Samvaad.

ElevenLabs is the realtime simulated caller (Arnav); the deployed Sarvam
Samvaad agent is the system under test (Shubh).  The wrapper deliberately
allows one record, one trial, and one attempt so a smoke test cannot fan out
into an expensive retry batch.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
EVA_ROOT = ROOT / "research" / "upstream" / "eva"
OUTPUT_ROOT = ROOT / "artifacts" / "eva_live"
RECORD_ID = "EMI-LIVE-001"
EVA_COMPONENT_METRICS = [
    "task_completion",
    "faithfulness",
    "agent_speech_fidelity",
    "turn_taking",
    "conciseness",
    "conversation_progression",
]


def _required_env() -> dict[str, str]:
    names = (
        "ELEVENLABS_API_KEY",
        "EVA_EN_USER_M",
        "GEMINI_API_KEY",
        "SARVAM_VOICE_AGENTS_API_KEY",
        "SARVAM_ORG_ID",
        "SARVAM_WORKSPACE_ID",
        "SARVAM_APP_ID",
        "SARVAM_APP_VERSION",
    )
    values = {name: os.getenv(name, "").strip() for name in names}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
    return values


def _build_config(
    *,
    run_id: str,
    dry_run: bool,
    record_ids: list[str] | None = None,
    num_trials: int = 1,
    app_version: int | None = None,
    output_root: Path = OUTPUT_ROOT,
    max_concurrent_conversations: int = 1,
    time_limit_seconds: int = 240,
):
    # EVA is an isolated upstream checkout; import only after its virtualenv is
    # active and its root is the working directory so computed fixture paths
    # resolve to the pinned EVA data/config tree.
    from eva.models.config import ModelConfig, RunConfig

    env = _required_env()
    os.environ["JUDGE_MODEL"] = "gemini-3.1-pro-preview"

    # Text validation uses the strongest available Gemini text deployment.
    # EVA's audio-fidelity validator retains its documented Flash alias. Both
    # are routed through the user's Google AI Studio key.
    model_list = [
        {
            "model_name": "gemini-3.1-pro-preview",
            "litellm_params": {
                "model": "gemini/gemini-3.1-pro-preview",
                "api_key": env["GEMINI_API_KEY"],
                "max_parallel_requests": 1,
            },
        },
        {
            "model_name": "gemini-3-flash-preview",
            "litellm_params": {
                "model": "gemini/gemini-3-flash-preview",
                "api_key": env["GEMINI_API_KEY"],
                "max_parallel_requests": 1,
            },
        },
    ]
    resolved_version = app_version or int(env["SARVAM_APP_VERSION"])
    model_name = f"sarvam-samvaad-v{resolved_version}"
    model = ModelConfig(
        s2s=model_name,
        s2s_params={
            "model": model_name,
            "api_key": env["SARVAM_VOICE_AGENTS_API_KEY"],
            "org_id": env["SARVAM_ORG_ID"],
            "workspace_id": env["SARVAM_WORKSPACE_ID"],
            "app_id": env["SARVAM_APP_ID"],
            "app_version": resolved_version,
        },
    )
    return RunConfig(
        model_list=model_list,
        model=model,
        framework="samvaad",
        domain="emi",
        run_id=run_id,
        record_ids=record_ids or [RECORD_ID],
        num_trials=num_trials,
        max_rerun_attempts=1,
        max_concurrent_conversations=max_concurrent_conversations,
        # 120s cut two of three pilot calls off mid-conversation, which scores as
        # not-finished rather than as whatever the agent actually did. A longer
        # ceiling does not make a looping agent behave; it just stops the harness
        # from destroying the evidence before the loop is visible.
        conversation_time_limit_seconds=time_limit_seconds,
        output_dir=output_root,
        # EVA first validates the realtime caller, then computes the complete
        # Accuracy (EVA-A) and Experience (EVA-X) component set only for valid
        # conversations.  Diagnostic metrics remain separate from release
        # truth and can be added by a versioned evaluator change later.
        metrics=EVA_COMPONENT_METRICS,
        preflight=True,
        dry_run=dry_run,
        log_level="INFO",
    )


async def _run(config) -> int:
    from eva.run_benchmark import run_benchmark

    return await run_benchmark(config)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Validate configuration; spend no provider credits.")
    parser.add_argument(
        "--confirm-live",
        action="store_true",
        help="Required for the single realtime ElevenLabs-to-Samvaad conversation.",
    )
    parser.add_argument(
        "--record-id",
        nargs="*",
        help="Campaign-2 scenario IDs to run instead of the campaign-1 smoke record.",
    )
    parser.add_argument(
        "--app-version",
        type=int,
        help="Override the committed agent version under test.",
    )
    parser.add_argument(
        "--time-limit",
        type=int,
        default=240,
        help="Seconds a single conversation may run before the harness ends it.",
    )
    args = parser.parse_args()
    if not args.dry_run and not args.confirm_live:
        parser.error("live execution requires --confirm-live")

    load_dotenv(ROOT / ".env", override=False)
    run_id = f"emi_eva_live_{datetime.now():%Y%m%d_%H%M%S}"
    os.chdir(EVA_ROOT)
    config = _build_config(
        run_id=run_id,
        dry_run=args.dry_run,
        record_ids=args.record_id or None,
        num_trials=1,
        app_version=args.app_version,
        time_limit_seconds=args.time_limit,
    )

    if not args.dry_run:
        run_dir = OUTPUT_ROOT / run_id
        if run_dir.exists():
            raise RuntimeError(f"Refusing to reuse live run directory: {run_dir}")

    print(
        json.dumps(
            {
                "mode": "dry_run" if args.dry_run else "live_single_conversation",
                "run_id": run_id,
                "record_ids": args.record_id or [RECORD_ID],
                "caller": "ElevenLabs realtime agent — Arnav",
                "system_under_test": "Sarvam Samvaad — Shubh",
                "max_provider_sessions": {"elevenlabs": 1, "samvaad": 1},
                "output_dir": str(OUTPUT_ROOT / run_id),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return asyncio.run(_run(config))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"EVA Samvaad run failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
