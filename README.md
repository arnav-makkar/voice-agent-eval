# Execution-Truth Evaluation & Self-Improvement for a Deployed Voice Agent

A deployed Hindi/Hinglish collections voice agent (Sarvam Indus) is evaluated,
diagnosed, and then improved by an autonomous search — with every claim graded
from an **append-only tool journal**, never from what the agent said.

| Tier | n | Baseline | Champion | Method |
| --- | ---: | ---: | ---: | --- |
| Text (headless channel) | 180 | 98 · 54.4% | **160 · 88.9%** | scripted callers, hidden goals, journal-hash grading |
| Phone (real handset) | 15 | 9 | **14** | human caller, 15 scripted cards, per-card ledger keys |
| Bot-to-bot (duplex audio) | 5 | 0.933 | **1.000** | synthetic caller over websocket, judged + deterministic metrics |

62 scenarios fixed, none broken (McNemar p ≈ 0). Five of six pre-registered
phone defects closed, zero regressions. Details, all recordings, and every
number: the site under [`dashboard/`](dashboard/) — `npm run dev`, then
http://localhost:3000.

## Why "execution truth"

A collections call's business outcome is a tool write — a promise logged, a
dispute filed, an escalation queued — not a sentence. The baseline agent's
defining failure was saying *"मैं आपका response note कर लेता हूँ"* and writing
nothing. Every tool is therefore served by a controlled service that appends
each invocation to a journal the agent cannot read back or edit, and **a claim
about a tool is decided by the journal alone**. Transcripts remain evidence of
what was said; they feed the speech-quality judges, never the task verdict.

## Repository layout

```
dashboard/                  The presentation site (Next.js shell + static pages)
  public/c2/                Seven-section walkthrough: overview → problem → instrument
                            → diagnosis → loop → results → calls → notes
  public/evidence/audio/    All 40 recorded calls (15+15 phone, 5+5 bot) with
                            per-call index.json: transcript, journal, verdicts
voice-agent-improvement/
  framework/                The evaluation framework
    tool_service.py         The gated tool backend + append-only journal
    evaluation/             Runners, verifier, adapters (text-chat, authoring,
                            telephony, duplex voice), graders
  scripts/                  Operational entry points (see below)
  dataset/                  Scenario generation (15 failure families)
  improvement/              Optimiser scaffolding used by the search stage
  artifacts/                Frozen benchmark, campaign results, run evidence,
                            the journal database
  research/eva-patches/     Tracked patches for the vendored voice harness
  tests/                    104 tests, including instrument regression guards
```

## The improvement loop

Sense (say-vs-do monitor over the journal) → distill (violations become replay
scenarios) → search (GEPA reflective prompt evolution against the live agent;
two-component candidates `{instructions, exemplars}` after MIPROv2) → gate
(held-out blind split, guardrail veto, McNemar paired flips, measured noise
floor) → deploy (authoring API, sha-pinned, parent sha = rollback). No human
wrote candidate text; the one post-campaign operational patch (the closing rule
names `end_interaction`) is declared wherever results are shown.

## Running things

```bash
# the site
cd dashboard && npm install && npm run dev

# the tool service (journal backend)
cd voice-agent-improvement
python scripts/run_tool_service.py           # needs AGENT_TOOL_SECRET

# phone tier, per card
bash scripts/preflight_phone.sh              # five checks; dial only on ALL GREEN
python scripts/place_phone_call.py --card 3
bash scripts/phone_call.sh 3                 # scores the journal after hang-up

# bot-to-bot (needs the vendored harness — research/eva-patches/README.md)
bash scripts/run_bot_call.sh EMI-VOICE-003

# tests
python -m pytest tests/
```

Secrets live in `.env` / `.env.local` (both gitignored): Sarvam voice-agents
key, org/workspace/app ids, `AGENT_TOOL_SECRET` (the tool-gate key; the legacy
`LOOPLINE_TOOL_SECRET` name is still accepted because the deployed platform's
tool definitions send the original header), and a short-lived dashboard JWT for
transcript retrieval.

## Honesty notes

- Historical run artifacts under `artifacts/` are byte-preserved evidence and
  contain the project's former internal codename; authored code and docs do not.
- The voice tiers are existence proofs (n = 15, n = 5); statistics live in the
  180-scenario text tier.
- Full limits — including the one card whose fix is confounded by language and
  the duplicate-write defect that moved rather than resolved — are on the site's
  final page.

## References

- **EVA** (ServiceNow Research) — the bot-to-bot harness and the
  Accuracy/Experience composite structure. github.com/ServiceNow/eva
- **GEPA** — reflective prompt evolution (optimize-anything API).
- **MIPROv2** (DSPy) — two-component candidate design.
- **τ-bench** — hashed end-state task grading.
- **Sarvam Indus / Samvaad** — the deployed agent platform.
