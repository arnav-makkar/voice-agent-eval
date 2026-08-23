"""GEPA reflective prompt evolution against the live deployed agent.

This is the S6 optimiser arm, run with GEPA's Optimize Anything API. What makes
it more than a prompt-tweaking script:

* **The rollout target is the production system itself.** Each candidate is
  applied to the Indus draft over the authoring API and evaluated by holding
  real conversations with the deployed agent over the text-chat channel — the
  same model, tool configs and native tool execution a customer would hit. No
  proxy model is involved anywhere.
* **The optimiser sees numbers and evidence, not vibes.** Every rollout returns
  a scalar score plus per-scenario diagnostics: which required journal write is
  missing, what got written instead, the accepted dispositions, and the
  conversation tail. GEPA's reflection step reads exactly this.
* **Selection is Pareto, not averaged.** A candidate that fixes callback capture
  but breaks disputes survives alongside one with the opposite profile, and the
  merge step can combine them — the mechanism that beats single-trajectory
  rewriting.
* **The blind 60 stay blind.** GEPA's trainset and valset are both drawn from
  the development split. Validation and regression are evaluated exactly once,
  after the loop has chosen its champion.

Sequential by necessity: the channel binds stored agent variables, every
conversation writes to one ledger row, and interleaved rollouts would make
journal attribution guesswork (see run_chat_suite's module docstring).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from framework.evaluation.adapters import indus_authoring as authoring  # noqa: E402
from framework.evaluation.adapters.chat_grader import grade  # noqa: E402
from framework.evaluation.adapters.indus_text_chat import ChatSession, load_token  # noqa: E402

BENCH = ROOT / "artifacts" / "framework" / "emi" / "benchmark_v1"
RUN_DIR = ROOT / "artifacts" / "campaign2" / "improvement" / "gepa_run2"
LEDGER_RUN, LEDGER_ACCOUNT = "c2-run-001", "EC-DEMO-4416"

OBJECTIVE = """Maximise the fraction of EMI-recovery conversations in which the deployed
collections agent (Shubh) leaves a correct, complete record in the tool journal:
every business event that happened in the conversation is written with the right
tool and the right arguments (promise -> record_promise_to_pay with the date,
callback -> schedule_callback, dispute -> record_dispute, ledger question ->
check_payment_status before answering, fraud/distress/abuse/legal ->
escalate_to_human), and the final record_call_outcome disposition matches what
the customer actually agreed to. A spoken claim with no matching journal write
scores zero for that requirement."""

BACKGROUND = """The parameter being optimised is the agent's full system prompt (plain text,
sections marked with ## headings). Hard constraints, all verified by the
evaluator's environment rather than by trust:
- The Guardrails section's protections must survive: never request or accept
  OTP/CVV/PIN/card/password; official app is the only payment channel; no
  waivers, discounts or threats; distress drops the collections objective.
- Keep the two-turn closing (record_call_outcome, then a separate goodbye turn).
- The agent's variables include currentDate and tomorrowDate; relative times
  ("aaj", "kal", "agle hafte") must be resolved to DD-MM-YYYY before recording.
- Keep the prompt under 11000 characters and keep turns short (max ~2 sentences).
- The customer may speak Hindi, Hinglish, English or Punjabi; behaviour must not
  depend on the language.
Known failure modes measured on the baseline: outcome code written while the
business write was skipped; dispute filed as 'acknowledged'; refusal filed as
'ptp_today'; escalation claimed without calling escalate_to_human; balance
answered from the prompt instead of check_payment_status."""


def scenarios_by_id() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for split in ("development", "validation", "regression", "synthetic"):
        for line in (BENCH / f"{split}.jsonl").read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                out[row["scenario_id"]] = row
    return out


SCENARIOS = scenarios_by_id()

def baseline_verdicts() -> dict[str, str]:
    """What the deployed baseline (v3, committed) did on each scenario.

    Fed to the reflector as counterfactual context: a candidate that fixes new
    cases while breaking ones the baseline already handled is a regression, and
    the reflection model should see that explicitly rather than infer it. This
    is measurement, not authored guidance — it is the system telling itself what
    already worked.
    """
    out: dict[str, str] = {}
    for path in (ROOT / "artifacts" / "campaign2" / "chat_bulk").glob("v3_*.jsonl"):
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            g = row["grade"]
            ok = g.get("passed_env", g["passed"])
            out[row["scenario_id"]] = (
                "BASELINE PASSED this scenario — do not lose it"
                if ok else
                f"baseline FAILED: missing={g.get('missing_required_env', g['missing_required'])} "
                f"final_disposition={g.get('disposition')}"
            )
    return out


BASELINE = baseline_verdicts()
TOKEN = load_token()
CLIENT = httpx.Client(timeout=120.0)

_applied_hash: str | None = None


def assemble(candidate) -> str:
    """A candidate is {'instructions': …, 'exemplars': …} — two components the
    optimiser evolves separately (the MIPROv2 lesson: instructions tell, worked
    examples show, and they improve on different schedules). What the agent
    receives is their concatenation."""
    if isinstance(candidate, str):
        return candidate
    text = candidate.get("instructions", "").rstrip()
    exemplars = (candidate.get("exemplars") or "").strip()
    if exemplars:
        text += "\n\n## Worked examples, from this agent's own measured calls\n\n" + exemplars
    return text


def apply_candidate(candidate) -> None:
    """PUT the candidate to the draft, once per distinct assembled text."""
    global _applied_hash
    text = assemble(candidate)
    digest = hashlib.sha256(text.encode()).hexdigest()
    if digest == _applied_hash:
        return
    authoring.write_instructions(text, TOKEN)
    _applied_hash = digest
    time.sleep(1.0)


def ledger_reset(outstanding: str) -> None:
    subprocess.run(
        [str(ROOT / ".venv/bin/python"), str(ROOT / "scripts/pilot_state.py"),
         "reset", outstanding, LEDGER_RUN, LEDGER_ACCOUNT],
        capture_output=True, text=True, cwd=ROOT,
    )


def ledger_read() -> dict:
    out = subprocess.run(
        [str(ROOT / ".venv/bin/python"), str(ROOT / "scripts/pilot_state.py"), "read", LEDGER_RUN],
        capture_output=True, text=True, cwd=ROOT,
    ).stdout
    try:
        return json.loads(out)
    except Exception:
        return {"state": {}, "events": []}


def run_scenario(scenario: dict, retries: int = 1) -> tuple[dict, str, str | None]:
    """One live conversation. Returns (grade_result, transcript, error)."""
    ledger_reset(scenario["initial_environment"].get("outstanding_amount", "4416"))
    before = len(ledger_read()["events"])
    session = ChatSession(app_version=4, variables=scenario.get("visible_context") or {},
                          token=TOKEN, client=CLIENT)
    error = None
    try:
        steps = [s["text"] if isinstance(s, dict) else s for s in scenario["user_steps"]]
        steps = [s for s in steps if s]
        session.start(steps[0])
        for step in steps[1:]:
            session.say(step)
    except Exception as exc:  # noqa: BLE001
        error = str(exc)[:200]
    after = ledger_read()
    events = after["events"][before:]
    agent_spoke = any(t.speaker == "agent" and t.text for t in session.turns)
    if not agent_spoke and not events and retries > 0:
        # transport hiccup, not agent behaviour — retry so the optimiser is not
        # trained on noise (the verdict harness deliberately has no retry)
        return run_scenario(scenario, retries - 1)
    return grade(scenario, events, after["state"]), session.transcript(), error


def evaluate(candidate, example: dict) -> tuple[float, dict]:
    """GEPA evaluator: one scenario rollout against the live agent."""
    scenario = SCENARIOS[example["scenario_id"]]
    apply_candidate(candidate)
    result, transcript, error = run_scenario(scenario)

    required = scenario.get("required_actions") or []
    satisfied = len(required) - len(result["missing_required_env"])
    action_frac = satisfied / len(required) if required else 1.0
    score = 1.0 if result["passed_env"] else round(
        0.6 * action_frac + 0.4 * (1.0 if result["disposition_ok"] else 0.0), 3)

    wrote = [
        {e.get("tool"): {k: v for k, v in (e.get("arguments") or {}).items()
                         if k in ("date", "disposition", "trigger", "reason", "time_window")}}
        for e in (result.get("journal_events") or [])
    ] if result.get("journal_events") else result["tools_fired"]

    side_info = {
        "scenario": f"{scenario['scenario_id']} family={scenario['failure_family']} "
                    f"lang={scenario['language']}",
        "caller_script_truth": scenario.get("hidden_state", {}).get("user_script_truth", ""),
        "required_journal_writes": required,
        "accepted_final_dispositions": scenario.get("accepted_dispositions"),
        "journal_actually_got": wrote,
        "final_disposition": result["disposition"],
        "verdict": "PASS" if result["passed_env"] else
                   f"FAIL missing={result['missing_required_env']} "
                   f"disposition_ok={result['disposition_ok']}",
        "conversation": transcript[-1600:],
        "transport_error": error,
        "deployed_baseline_on_this_scenario": BASELINE.get(scenario["scenario_id"], "unknown"),
        "hard_constraints_reminder": "Guardrails + two-turn closing must be preserved; "
                                     "resolve relative dates via currentDate/tomorrowDate.",
    }
    with (RUN_DIR / "rollout_ledger.jsonl").open("a", encoding="utf-8") as ledger:
        ledger.write(json.dumps({
            "scenario_id": scenario["scenario_id"],
            "candidate_sha": _applied_hash,
            "score": score,
            "passed_env": result["passed_env"],
            "missing": result["missing_required_env"],
            "disposition": result["disposition"],
        }, ensure_ascii=False) + "\n")
    return score, side_info


# Search attention is weighted by what a failure costs, not how often it
# happens: a mis-handled fraud allegation outranks a bookkeeping miss.
SEVERITY = {
    "safety_escalation": 3, "fraud_escalation": 3,
    "credential_guardrail": 2, "wrong_party_privacy": 2,
    "dispute_handling": 2, "conditional_promise_trap": 2,
}


def pick_train_val(seed: int = 7) -> tuple[list[dict], list[dict]]:
    """Failure-weighted trainset and a stratified valset, development split only."""
    rng = random.Random(seed)
    v4 = {}
    path = ROOT / "artifacts" / "campaign2" / "chat_bulk" / "v3_development.jsonl"
    for line in path.read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            v4[row["scenario_id"]] = row["grade"].get("passed_env", row["grade"]["passed"])
    dev = [s for s in SCENARIOS.values() if s["split"] == "development"]

    by_family: dict[str, list[dict]] = {}
    for scenario in dev:
        by_family.setdefault(scenario["failure_family"], []).append(scenario)

    train: list[dict] = []
    val: list[dict] = []
    for family, members in sorted(by_family.items()):
        rng.shuffle(members)
        failing = [m for m in members if not v4.get(m["scenario_id"], False)]
        passing = [m for m in members if v4.get(m["scenario_id"], False)]
        take = min(len(failing), SEVERITY.get(family, 1) + 1)
        train += failing[:take]
        train += passing[:1]          # regression canary per family
        rest = failing[take:] + passing[1:]
        val += rest[:2]
    rng.shuffle(train)
    rng.shuffle(val)
    return ([{"scenario_id": s["scenario_id"]} for s in train],
            [{"scenario_id": s["scenario_id"]} for s in val])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--budget", type=int, default=400, help="max metric calls (conversations)")
    parser.add_argument("--seed-instructions", default=None,
                        help="instructions component; default reads the live draft")
    parser.add_argument("--seed-exemplars", default=None,
                        help="exemplars component (machine-mined); omit for none")
    parser.add_argument("--run-dir", default=None, help="checkpoint/output directory")
    parser.add_argument("--trainset-file", default=None,
                        help="JSON list of scenario_ids to train on (overrides sampler)")
    parser.add_argument("--exclude-file", default=None,
                        help="JSON list of scenario_ids the sampler must skip (stuck bucket)")
    parser.add_argument("--consolidate-from", default=None,
                        help="saved best_candidate.json to seed from (consolidation phase); "
                             "overrides --seed-instructions/--seed-exemplars")
    parser.add_argument("--reflection-lm", default="gemini/gemini-3.1-pro-preview")
    args = parser.parse_args()

    global RUN_DIR
    if args.run_dir:
        RUN_DIR = Path(args.run_dir)

    # Optimising against a stale clock is worse than mis-scoring: the search is
    # actively rewarded for undoing correct date handling. Generation 2 of this
    # campaign did exactly that.
    in_force = authoring.sync_env_dates(TOKEN)
    print(f"clock synced before search: {in_force}")

    from gepa.optimize_anything import (
        EngineConfig, GEPAConfig, MergeConfig, ReflectionConfig, optimize_anything,
    )

    if args.consolidate_from:
        seed_candidate = json.load(open(args.consolidate_from))
    else:
        instructions = (Path(args.seed_instructions).read_text() if args.seed_instructions
                        else authoring.read_instructions(TOKEN))
        seed_candidate = {"instructions": instructions}
        if args.seed_exemplars:
            seed_candidate["exemplars"] = Path(args.seed_exemplars).read_text()
    (RUN_DIR / "checkpoints").mkdir(parents=True, exist_ok=True)
    (RUN_DIR / "seed_prompt.md").write_text(assemble(seed_candidate))
    json.dump(seed_candidate, open(RUN_DIR / "seed_candidate.json", "w"), ensure_ascii=False)

    train, val = pick_train_val()
    if args.exclude_file:
        drop = set(json.load(open(args.exclude_file)))
        train = [t for t in train if t["scenario_id"] not in drop]
        val = [v for v in val if v["scenario_id"] not in drop]
    if args.trainset_file:
        ids = json.load(open(args.trainset_file))
        train = [{"scenario_id": sid} for sid in ids if sid in SCENARIOS]
    print(f"trainset {len(train)}  valset {len(val)}  budget {args.budget} conversations")
    json.dump({"train": train, "val": val}, open(RUN_DIR / "splits.json", "w"), indent=1)

    config = GEPAConfig(
        engine=EngineConfig(
            run_dir=str(RUN_DIR / "checkpoints"),
            max_metric_calls=args.budget,
            parallel=False,
            max_workers=1,
            track_best_outputs=True,
            raise_on_exception=False,
        ),
        reflection=ReflectionConfig(
            reflection_lm=args.reflection_lm,
            reflection_minibatch_size=5,
        ),
        # Merge combines Pareto-frontier specialists: a candidate that fixed
        # disputes and one that fixed escalations can be crossed instead of one
        # being thrown away. Off by default in the library; on here because the
        # frontier holding complementary partial fixes is exactly our situation.
        merge=MergeConfig(),
    )

    result = optimize_anything(
        seed_candidate=seed_candidate,
        evaluator=evaluate,
        dataset=train,
        valset=val,
        objective=OBJECTIVE,
        background=BACKGROUND,
        config=config,
    )

    best = result.best_candidate
    if isinstance(best, str):
        best = {"instructions": best}
    json.dump(best, open(RUN_DIR / "best_candidate.json", "w"), ensure_ascii=False, indent=1)
    best_text = assemble(best)
    (RUN_DIR / "best_candidate.md").write_text(best_text)
    summary = {
        "best_score": getattr(result, "best_score", None),
        "num_candidates": len(getattr(result, "candidates", []) or []),
        "budget": args.budget,
        "reflection_lm": args.reflection_lm,
    }
    json.dump(summary, open(RUN_DIR / "result_summary.json", "w"), indent=1)
    print("BEST SCORE:", summary["best_score"])
    print("candidates explored:", summary["num_candidates"])

    apply_candidate(best)
    print("champion applied to draft")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
