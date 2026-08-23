"""Run the frozen benchmark against the deployed agent over the text-chat channel.

This is the bulk text tier. It talks to the same deployed Indus agent the voice
and phone tiers use — same prompt, same six tool configs, native execution —
over the REST text-chat channel the browser console uses, so no proxy model and
no DOM automation is involved.

Why it is sequential
--------------------
The channel gives no way to override agent variables per request: six candidate
field names were probed and every one was ignored in favour of the values stored
on the agent. ``campaignId`` is what the tools map to ``run_id``, so every
conversation writes to the same ledger row. Running two at once would make it
impossible to say which conversation produced which write, so scenarios run one
at a time with the ledger reset in between and the journal delta read straight
after. Slower, but every tool attribution is exact rather than inferred.

Tool truth comes from the journal delta, never from ``debug_logs``. The debug
logs are kept alongside as a trace of what the runtime attempted, which is what
makes an attempted-but-failed write visible instead of silently absent.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from framework.evaluation.adapters.indus_text_chat import (  # noqa: E402
    ChatSession,
    load_token,
)
from framework.evaluation.adapters.chat_grader import grade  # noqa: E402

BENCH = ROOT / "artifacts" / "framework" / "emi" / "benchmark_v1"
LEDGER_RUN = "c2-run-001"          # fixed by the agent's stored campaignId
LEDGER_ACCOUNT = "EC-DEMO-4416"


def ledger_state() -> dict:
    out = subprocess.run(
        [str(ROOT / ".venv/bin/python"), str(ROOT / "scripts/pilot_state.py"), "read", LEDGER_RUN],
        capture_output=True, text=True, cwd=ROOT,
    ).stdout
    try:
        return json.loads(out)
    except Exception:
        return {"state": {}, "events": []}


def ledger_reset(outstanding: str) -> None:
    subprocess.run(
        [str(ROOT / ".venv/bin/python"), str(ROOT / "scripts/pilot_state.py"),
         "reset", outstanding, LEDGER_RUN, LEDGER_ACCOUNT],
        capture_output=True, text=True, cwd=ROOT,
    )


def caller_lines(scenario: dict) -> list[str]:
    """The caller's spoken turns.

    A step is a dict carrying the line plus authoring metadata (``intent``,
    ``notes``); only the spoken text may reach the agent — sending the intent
    label would tell it what the scenario is testing.
    """
    lines: list[str] = []
    for step in scenario.get("user_steps") or []:
        text = step.get("text") if isinstance(step, dict) else step
        if text:
            lines.append(str(text))
    return lines


def run_split(split: str, out_path: Path, limit: int | None, app_version: int) -> None:
    scenarios = [json.loads(line) for line in (BENCH / f"{split}.jsonl").read_text().splitlines() if line.strip()]
    if limit:
        scenarios = scenarios[:limit]

    done: set[str] = set()
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            if line.strip():
                done.add(json.loads(line)["scenario_id"])
        print(f"  resuming: {len(done)} already recorded")

    token = load_token()
    passed = sum(1 for line in out_path.read_text().splitlines()
                 if line.strip() and json.loads(line)["grade"]["passed"]) if out_path.exists() else 0

    with httpx.Client(timeout=120.0) as client, out_path.open("a", encoding="utf-8") as sink:
        for index, scenario in enumerate(scenarios, 1):
            sid = scenario["scenario_id"]
            if sid in done:
                continue
            started = time.time()
            ledger_reset(scenario["initial_environment"].get("outstanding_amount", "4416"))
            before = len(ledger_state()["events"])

            session = ChatSession(
                app_version=app_version,
                variables=scenario.get("visible_context") or {},
                token=token,
                client=client,
            )
            error = None
            try:
                steps = caller_lines(scenario)
                if not steps:
                    raise RuntimeError("scenario has no user_steps")
                session.start(steps[0])
                for step in steps[1:]:
                    session.say(step)
            except Exception as exc:  # noqa: BLE001
                error = str(exc)[:300]

            after = ledger_state()
            events = after["events"][before:]
            result = grade(scenario, events, after["state"])
            passed += 1 if result["passed"] else 0

            sink.write(json.dumps({
                "scenario_id": sid,
                "split": split,
                "family": scenario.get("failure_family"),
                "language": scenario.get("language"),
                "persona": (scenario.get("persona") or {}).get("id"),
                "app_version": app_version,
                "interaction_id": session.interaction_id,
                "transcript": session.transcript(),
                "attempted_tools": session.attempted_tools(),
                "journal_events": events,
                "grade": result,
                "error": error,
                "seconds": round(time.time() - started, 1),
            }, ensure_ascii=False) + "\n")
            sink.flush()

            flag = "ok " if result["passed"] else "FAIL"
            print(f"  [{index}/{len(scenarios)}] {sid} {flag} "
                  f"{result['disposition']} tools={result['tools_fired']} "
                  f"{round(time.time()-started,1)}s"
                  + (f" ERR {error}" if error else ""), flush=True)

    total = len(scenarios)
    print(f"  {split}: {passed}/{total} passed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="development")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--app-version", type=int, default=3)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    # The agent's clock is set from the real calendar before anything runs, and
    # the grader reads the same values back. A stale currentDate silently
    # mis-scores every relative-date scenario, so this is not optional.
    from framework.evaluation.adapters import indus_authoring
    in_force = indus_authoring.sync_env_dates()
    print(f"  clock synced: {in_force}")

    out = Path(args.out) if args.out else (
        ROOT / "artifacts" / "campaign2" / "chat_bulk" / f"v{args.app_version}_{args.split}.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    run_split(args.split, out, args.limit, args.app_version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
