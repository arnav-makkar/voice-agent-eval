# Evaluation & self-improvement framework

The engine room behind the results presented in [`../dashboard`](../dashboard):
a governed evaluate → diagnose → improve → release loop around one deployed
Sarvam Indus voice agent, graded from an append-only tool journal.

All EasyCredit data is fictional. Credentials live in `.env` / `.env.local`
(gitignored). Everything below assumes this directory as the working directory.

## The three jobs, kept separate

1. **Evaluation** — versioned multi-turn scenarios run against the deployed
   agent through three channels (headless text-chat, outbound telephony,
   duplex voice), with tool effects captured by an isolated tool service.
   Deterministic journal-state grading decides task truth; judge models score
   speech quality only.
2. **Improvement** — failures distilled from the journal feed a reflective
   prompt search (GEPA; two-component candidates after MIPROv2) whose evaluator
   is the benchmark grader itself.
3. **Release governance** — a held-out blind split touched once per rung, a
   guardrail veto, McNemar paired flips, and a measured noise floor. Winners
   deploy through the authoring API with the sha pinned; the parent sha is the
   rollback.

## Campaign results (Aug 2026)

| Tier | n | Baseline | Champion |
| --- | ---: | ---: | ---: |
| Text | 180 | 98 | **160** |
| Phone | 15 | 9 | **14** |
| Bot-to-bot (accuracy composite) | 5 | 0.933 | **1.000** |

Canonical artifacts: `artifacts/campaign2/results_master.json` (every number on
the site), `artifacts/campaign2/phone/` (per-card contracts and outcomes),
`artifacts/campaign2/bot_to_bot/` (per-metric grid and ledger hygiene),
`artifacts/framework/emi/benchmark_v1/` (the frozen scenario suite).

## Directory map

```
framework/
  tool_service.py            gated tool backend + append-only journal (SQLite)
  evaluation/
    runner.py, verifier.py   scenario execution and journal-state grading
    adapters/
      indus_text_chat.py     headless REST channel of the deployed agent
      indus_authoring.py     read/write the deployed prompt; clock hygiene
      chat_grader.py         env-conditioned + strict grading
scripts/                     operational entry points (each is documented in-file)
  run_tool_service.py        start the journal backend
  preflight_phone.sh         five checks incl. an end-to-end journal probe
  place_phone_call.py        dial one card with per-call ledger key + live clock
  phone_call.sh              score a card from the journal after hang-up
  run_bot_call.sh            place → repair transcript → re-score, one voice call
  fetch_call_logs.py         transcripts/recordings from platform analytics
  gepa_optimize.py           the search stage against the live agent
dataset/                     scenario generation across 15 failure families
improvement/                 optimiser scaffolding
research/eva-patches/        tracked patches for the vendored voice harness (see its README)
tests/                       104 tests, incl. instrument regression guards
```

## Quick start

```bash
python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m pytest tests/            # 104 passing

.venv/bin/python scripts/run_tool_service.py # needs AGENT_TOOL_SECRET
bash scripts/preflight_phone.sh              # never dial on RED
```

The tool gate reads `AGENT_TOOL_SECRET` (header `X-Agent-Tool-Key`); the legacy
`LOOPLINE_*` names remain accepted because the deployed platform's tool
definitions still send the original header. Historical artifacts under
`artifacts/` are byte-preserved evidence and may contain that former codename.
