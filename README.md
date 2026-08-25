# Evaluation and self-improvement for voice agents

A framework that grades a voice agent on the records it leaves behind, turns its
failures into replayable tests, and lets a search rewrite the agent against them.
Validated end to end on a live Hindi/Hinglish EMI collections agent deployed on
Sarvam Indus, across 200 real conversations.

**[See the full walkthrough, with every recording and every number →](https://sarvam-voice-agent-eval.vercel.app)**

## The idea

A collections call's business outcome is a tool write: a promise logged, a
dispute filed, an escalation queued. Not a sentence. The baseline agent's
defining failure was saying *"मैं आपका response note कर लेता हूँ"* and writing
nothing — a call that reads perfectly in the transcript and changed nothing.

So every tool is served by a backend that appends each call to a journal the
agent can add to but never read back or edit, and **task success is decided by
that journal alone**. Transcripts feed the conversation-quality judges; they
never decide whether the job got done.

## Results

| Tier | n | Baseline | After | Graded by |
| --- | ---: | ---: | ---: | --- |
| Text | 180 | 98 | **160** | journal end-state hash |
| Phone, dialled by hand | 15 | 9 | **14** | same, on a real handset |
| Bot-to-bot voice | 5 | 4 | **5** | same, synthetic caller over live audio |

62 situations fixed, none broken, McNemar p ≈ 0. Held out from the search
entirely: 33 → 59 of 60. Thirty situations written *after* the campaign closed:
18 → 29.

Judged metrics (faithfulness, conciseness, progression) are scored 0–100 on
five-level rubrics by one judge across both voice tiers — spec in
[`RUBRIC.md`](voice-agent-improvement/artifacts/campaign2/rescore/RUBRIC.md),
every prompt and response in `rescore/judge_scores.json`.

## The loop

**Notice** a call whose journal contradicts itself → **group** repeats into a
replayable test → **search** rewrites the agent's instructions (GEPA, scored by
the benchmark grader itself) → **gate** on four checks: unseen split, safety
veto, McNemar, measured noise floor → **ship** fingerprinted, and the winner
becomes the next baseline.

The search optimises accuracy only. Conversation quality is measured on every
call and deliberately left out of the objective.

## Layout

```
dashboard/public/            The site: six pages, plus all 40 recordings
voice-agent-improvement/
  framework/                 Tool service with the append-only journal, graders,
                             channel adapters (text, telephony, duplex voice)
  scripts/                   Entry points: run a tier, rescore, rebuild the site
  artifacts/                 Frozen benchmark, campaign evidence, run records
  research/eva-patches/      Patches for the vendored voice harness
  tests/                     104 tests, including instrument regression guards
```

## Running it

```bash
cd dashboard && npm install && npm run dev     # the site, localhost:3000
```

```bash
cd voice-agent-improvement
python scripts/run_tool_service.py             # journal backend, needs AGENT_TOOL_SECRET
bash scripts/preflight_phone.sh                # dial only on ALL GREEN
python -m pytest tests/
```

Secrets live in `.env` (gitignored): Sarvam voice-agent key, org/workspace/app
ids, `AGENT_TOOL_SECRET`, and `GEMINI_API_KEY` for the judges.

## Limits

The voice tiers are existence proofs, not statistics — n = 15 and n = 5. The
statistics live in the 180-conversation text tier. Two rounds show the loop
repeats; they do not show that gains compound, and that is not claimed. One
phone card's fix is confounded by a language switch. Collection rate was never
an objective.

Run artifacts under `artifacts/` are byte-preserved evidence and still carry the
project's former internal codename; authored code and docs do not.

## Built on

[EVA](https://github.com/ServiceNow/eva) (ServiceNow Research) for the
bot-to-bot harness and the two-composite structure, with its task-completion
core replaced by journal grading · **GEPA** for reflective prompt evolution ·
**MIPROv2** (DSPy) for the two-part candidate design · **τ-bench** for
end-state grading · **Sarvam Indus / Samvaad** as the deployed platform.
