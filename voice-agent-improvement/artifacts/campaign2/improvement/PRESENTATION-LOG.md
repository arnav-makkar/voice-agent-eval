# Reflex Run — presentation log

Everything worth citing, captured as it happened. Times are local (IST).

## Run identity
- **Agent**: `EasyCredit--4e112b0d-9931`, committed baseline **v3**; all candidates land on the **draft** (staging). Nothing committed by this run.
- **Substrate**: Indus app-runtime text-chat REST channel — real conversations with the deployed agent, native tool execution. No proxy model.
- **Reward**: read from the append-only tool journal, never from transcript text.
- **Optimiser**: GEPA Optimize Anything; reflector **gemini-3.1-pro-preview**; Pareto selection + merge enabled.
- **Candidate**: two components `{instructions, exemplars}` (MIPROv2 graft).
- **Lineage guarantee**: seed = committed v3 instructions verbatim; exemplars machine-mined from v3's own passing calls; every later mutation model-proposed. **No human-authored candidate text.**

## Pre-flight (23 Aug, 22:2x)
- Dashboard JWT refreshed: 12.0 h validity.
- Authoring API reachable; draft readable.
- Tunnel HTTP 200; tool service HTTP 200.
- Assets present: v3 seed (5,723 chars), mined exemplars, fresh blind sets (hashed).

## P1 — Noise probe (00:32–00:47) · 90 conversations

The v3 seed was applied to the draft and the **same prompt** was run twice over a
45-scenario stratified probe (3 per family, development split), identical harness
settings both times.

| | value |
|---|---|
| run 1 | 23 / 45 |
| run 2 | 22 / 45 |
| scenarios that flipped verdict | **1** |
| **flip rate** | **2.2%** |
| σ(pass count) at n=30 / 60 / 180 | 0.58 / **0.82** / 1.41 |

**Gate rule derived from it:** a blind-60 delta below **1.6 passes** is reported as
*within noise* — gains and losses alike.

**Why this matters for the claim.** The evaluation is far more deterministic than
assumed: the agent reproduces its own verdict on 97.8% of scenarios. So a blind-60
improvement of 2+ passes is signal, not luck, and the 180-scenario paired
comparison has σ≈1.4 — small against the deltas being measured. This is the number
that turns "it improved" into "it improved beyond measurement noise", and it was
measured **before** any candidate existed, so it cannot have been chosen to flatter
a result.

## P2 — Generation 1, explore (00:47–02:04) · 380 conversations

GEPA Optimize Anything, reflector `gemini-3.1-pro-preview`, seeded from the
committed v3 instructions plus machine-mined exemplars. 10 candidates explored.

**Valset trajectory** (30 dev-held scenarios, never the blind set):

| iteration | best valset score |
|---|---|
| 0 (seed = committed v3) | 0.723 |
| 1 | 0.743 |
| 3 | 0.757 |
| 4 | 0.787 |
| 8–9 | **0.797** |

**Both candidate components evolved** — the MIPROv2 graft working as intended:

| component | seed | champion |
|---|---|---|
| instructions | 5,723 chars | 8,007 chars |
| exemplars (machine-mined worked examples) | 1,873 chars | 6,382 chars |

Section-level growth in the instructions: Tools +711, Closing +593, Objective
+564, Guardrails +308, The account +84. The section *structure* was preserved —
GEPA deepened the existing contract rather than rewriting the agent's identity.

### The finding that makes the claim
The generation-zero ablation (v5) needed a **human edit** to repair its closing
logic. Given proper feedback, GEPA **rediscovered that rule on its own**:

> *"You cannot log `ptp_today`, `fptp`, `callback`, `dispute`, or `escalation`
> unless you have already called the corresponding business tool. If you missed
> it, call the business tool NOW instead, say a brief acknowledgment, and call
> `record_call_outcome` on your next turn."*

That is the say-versus-do coupling — the campaign's central defect — stated as a
precondition, authored by the optimiser. It also independently addressed phone
defect **P6** ("does not end the call"):

> *"When the outcome is clear … move to close immediately without waiting for the
> customer to say goodbye."*

**Why it matters:** the human edit that contaminated v5 is no longer needed. The
difference between the two runs is not a better model — it is that this loop feeds
the reflector per-scenario journal evidence and counterfactual baseline verdicts,
so the insight was *derivable* from the feedback rather than requiring a person to
notice it.

## P3 — Generation 1 explore, development verdict (02:04–02:23) · 105 conversations

**v3 59/105 → gen-1-explore 77/105 (+18)** on the development split.

| family | v3 | g1-explore | Δ |
|---|---|---|---|
| amount_question | 0/7 | **7/7** | +7 |
| safety_escalation | 0/7 | **6/7** | +6 |
| fraud_escalation | 3/7 | **7/7** | +4 |
| dispute_handling | 1/7 | 4/7 | +3 |
| explicit_refusal | 5/7 | 7/7 | +2 |
| today_promise | 0/7 | 1/7 | +1 |
| conditional_promise_trap | 0/7 | 1/7 | +1 |
| **callback_capture** | 7/7 | **1/7** | **−6** |

**The regression is the point.** A search that only maximises an average would have
shipped this: +18 net looks excellent, and a family that used to work perfectly is
now broken. The triage step caught it automatically — **7 regressions, 20 stuck,
17-scenario consolidation trainset** — and handed the regressions plus a protected
sample of the champion's own fixes to a second short GEPA run seeded from the
champion. This is the systemic replacement for the human repair that contaminated
the earlier ablation.

**Stuck bucket (20)** — failed under *both* v3 and the champion with an identical
missing-write signature, i.e. two distinct prompts and every reflection's attention
did not move them: today_promise 6, conditional_promise_trap 6, already_paid 5,
dispute_handling 2, safety_escalation 1. These are excluded from generation 2's
*search attention* but still scored in every verdict, and re-tested each generation.

## P4–P5 — Generation 1 final (02:23–03:19) · 100 + 180 conversations

Consolidation ran on the 7 regressions + 10 protected fixes and **won the pick**
(valset 0.810 vs explore's 0.797), so gen-1 final = the consolidated candidate.

### Rung 1 — v3 → generation 1, all 180 scenarios

| | v3 | gen-1 | Δ |
|---|---|---|---|
| **overall** | 98/180 | **136/180** | **+38 (+38.8% relative)** |
| **blind (validation+regression)** | 34/60 | **49/60** | **+15** |
| development | 59/105 | 81/105 | +22 |
| validation | 17/30 | 24/30 | +7 |
| regression | 17/30 | 25/30 | +8 |
| synthetic | 5/15 | 6/15 | +1 |
| guardrail families | 42/72 | **63/72** | +21 |
| words per agent turn | 16.0 | 15.9 | quality held |

**Statistics:** paired flips 48 fixed / 10 broken, **McNemar exact p ≈ 0.0**.
Blind rate 0.817, Wilson 95% CI **(0.701, 0.894)**. The delta is 15 passes against
a measured noise threshold of 1.6 — **signal by more than nine times the bar**.

| family | v3 | gen-1 | Δ |
|---|---|---|---|
| amount_question | 0/12 | 11/12 | +11 |
| safety_escalation | 2/12 | 12/12 | +10 |
| fraud_escalation | 6/13 | 13/13 | +7 |
| dispute_handling | 2/12 | 8/12 | +6 |
| already_paid | 2/12 | 6/12 | +4 |
| explicit_refusal | 8/12 | 12/12 | +4 |
| conditional_promise_trap | 0/12 | 4/12 | +4 |
| **callback_capture** | 12/12 | **2/12** | **−10** |

### The callback regression — SUPERSEDED, see the correction below
> The diagnosis in this section was **wrong** and is kept only to show the trail.
> The real cause and the corrected numbers are in the final section.
Every failing callback wrote **the exemplar's literal values** — `24-08-2026`,
`10 AM to 11 AM` — regardless of what the caller said. Transcript evidence: caller
says *"kal 10 se 11"*, agent replies correctly *"कल सुबह दस से ग्यारह बजे"*, and the
journal records the exemplar's date.

**This is the MIPROv2 hazard, observed live:** a worked example teaches the
*pattern* (fire `schedule_callback` before closing) and simultaneously teaches the
*content* (that specific date), and the model copies both. The agent's spoken turn
was right; only the recorded argument was borrowed. It is exactly the say-versus-do
gap the journal-truth grader exists to catch — here caused by our own intervention.

**Not patched by hand.** The failures now sit in generation 2's refreshed trainset,
and the exemplars are an editable candidate component, so the loop has both the
evidence and the actuator to fix it. Whether it does is reported either way.

## P6–P8 — Generation 2 and the final ladder (03:19–06:03)

Generation 2 seeded from the gen-1 champion, trainset refreshed from gen-1's
residual failures, 31 stuck scenarios excluded from search. It opened at valset
**0.927** (gen-1 opened at 0.723) and **never moved off it across 15 iterations**.

### Final ladder — every rung machine-lineage

| | overall /180 | blind /60 | fresh blind /30 |
|---|---|---|---|
| **v3 BASE (committed)** | 98 | 34 | 15 |
| **generation 1** | **136** | **49** | 22 |
| generation 2 | 137 | 50 | 25 |

| rung | overall | blind | McNemar | guardrails | words/turn |
|---|---|---|---|---|---|
| v3 → gen-1 | 98→136 **(+38, +38.8%)** | 34→49 **signal** | ±48/−10, **p≈0.0** | 42→**63** | 16.0→15.9 |
| gen-1 → gen-2 | 136→137 | 49→50 **NOISE** | ±6/−5, p=1.0 | 63→60 **VETO** | 15.9→15.8 |
| v3 → gen-2 | 98→137 (+39) | 34→50 signal | ±51/−12, p≈0.0 | 42→60 | 16.0→15.8 |

**The gate selected generation 1**, not the later or higher-scoring candidate:
gen-2's blind gain of +1 is below the measured 1.6 noise threshold, and its
guardrail families dropped 63→60 — a veto that is not tradeable against a
one-pass gain. The champion on the draft is generation 1. *This is the system
refusing to promote its own newest work, on rules fixed before the run started.*

**Headline, defensible:** **+38.8% relative on the frozen 180** (98→136),
**+44% on the blind 60** (34→49), **p ≈ 0.0**, guardrails **improved** (42→63),
turn length unchanged. On 30 scenarios generated after the fact and never touched
by any search phase: **v3 15/30 → gen-1 22/30 → gen-2 25/30**.

### Generation 2 is a negative result, and it is worth presenting
The compounding hypothesis — "each generation improves on the last using evidence
the last one created" — **did not hold here**. Gen-2 spent 300 conversations and
produced a delta indistinguishable from noise. The reason is visible in the data:
gen-1 had already taken every fixable failure its search could reach, and the
31-scenario stuck bucket (today_promise 10, conditional_promise_trap 8,
already_paid 6) is exactly the residue two distinct prompts could not move. The
loop reached its own stopping condition rather than manufacturing motion, which is
the behaviour the design asked for — but it means the honest claim is *one*
verified generation plus a demonstrated stopping rule, not a compounding ladder.

### Known open defect, unpatched by hand
`callback_capture` 12/12 → 2/12. Cause: **exemplar over-copying** — the agent
writes the worked example's literal `24-08-2026 / 10 AM to 11 AM` instead of
resolving the caller's "kal". Generation 2 had the evidence and the actuator (the
exemplars are an editable component) and did not fix it. The fix is a *framework*
change, not a prompt edit: the exemplar miner must redact volatile fields (dates,
time windows) to placeholders so the example teaches the pattern without donating
its content. That change plus a re-run is the honest next step, and would likely
recover ~10 passes on top of 136.

## Independent confirmation — the label-free monitor agrees

The seven journal invariants need no transcript, no ground truth and no QA label —
they are the production sensing layer. Run over every conversation:

| version | conversations flagged | precision | dominant violation |
|---|---|---|---|
| v3 BASE | **23** | 1.00 | promise disposition with no promise row (13), escalation code with no escalation call (8) |
| generation 1 | **2** | 1.00 | business write with no outcome (2) |
| generation 2 | 5 | 1.00 | business write with no outcome (3), escalation code without call (2) |

**Say-versus-do violations fell 23 → 2** — measured by a detector that shares no
code with the benchmark grader and never sees the scenario script. This is the
number that transfers to production: the same check runs on live traffic, at
precision 1.00, with no labels required.

## What is on the draft right now
`gen1_final.json` — instructions 8,007 chars + exemplars, applied to the **draft
(staging)**. Nothing committed; serving traffic still runs v3. Rollback is one API
call.

## The five claims this run supports
1. **A self-improvement loop that works on the deployed system.** 1,600+ real
   conversations with the live agent; every candidate applied over the authoring
   API; every reward read from the append-only journal.
2. **+38.8% relative improvement, statistically established.** 98→136/180,
   blind 34→49/60, McNemar p≈0.0, against a noise floor measured *before* any
   candidate existed (flip rate 2.2%, σ₆₀ = 0.82).
3. **Held-out generalisation.** On 30 scenarios generated after the fact with zero
   search exposure: 15/30 → 22/30 (gen-1), 25/30 (gen-2).
4. **The gate has teeth.** It refused to promote generation 2 — blind gain within
   noise, guardrail veto — and selected generation 1 instead.
5. **Safety improved, quality held.** Guardrail families 42→63; words per agent
   turn 16.0→15.9.

## The three things to say before being asked
- **Generation 2 is a negative result.** The compounding hypothesis did not hold;
  the loop hit its stopping condition. One verified generation, plus a
  demonstrated stopping rule.
- **`callback_capture` regressed 12/12→2/12** from exemplar over-copying, and was
  left unpatched to keep the lineage clean. The fix is in the miner, not the prompt.
- **Chat only.** Voice transfer (15 phone cards + 5 bot-to-bot on the champion) is
  the S7 step and is not yet measured.

---

# CORRECTION — the callback regression was an environment fault, not an agent fault

Written 24 Aug ~05:50 after the overnight run, before any of it reached a slide.

## What I claimed, and why it was wrong
I reported that generation 1 broke `callback_capture` (12/12 → 2/12) by copying
the worked example's literal date. The mechanism was plausible, the evidence
looked consistent — every failing call booked `24-08-2026`, and the exemplar
contained a fixed date. It was still wrong.

## How it was falsified
Two redaction variants of the exemplar miner were built and probed against the
live agent: angle-bracket placeholders, then values annotated with their
derivation. **Both booked exactly the same `24-08-2026`.** If the exemplar were
the source, removing it would have changed the output. It did not, so the
exemplars were not the cause.

## The real cause
| | booked | why |
|---|---|---|
| v3 baseline | `23-08-2026` | reads the injected `tomorrowDate` variable |
| generation 1 | `24-08-2026` | resolves "kal" against the **real calendar** |

The agent's stored `currentDate` was `22-08-2026` — correct when set, one day
stale by the time the run finished. Generation 1's evolved prompt had made the
agent *compute* relative dates rather than *read the variable*, so it answered
correctly for the real world and was graded against yesterday.

**Correcting the stored date to `23-08-2026` took the same family to 11/11, with
no change to the prompt.**

## Why this is the more interesting finding
In production `currentDate` *is* the real date, so generation 1's behaviour would
be correct there and v3's variable-reading would be equally correct — the two only
diverge because our harness lied about the day. The optimiser did not regress; it
became more robust in a way our test rig could not represent, and the rig failed
first. That is a harness defect surfaced by an improvement, and it is the third
one this campaign has found (after the Samvaad silence-stream and the
substring-matching guardrail metric).

## What was done about it
- Stored `currentDate`/`tomorrowDate` corrected on the agent; grader `ENV_DATES`
  synced to match.
- The exemplar miner was **reverted** to the version that produced generation 1
  and verified to reproduce its exemplars byte-for-byte — the change had been made
  on a diagnosis that turned out to be false, so it does not belong in the code.
- **Both v3 and generation 1 are being re-measured on the corrected environment**,
  because comparing a baseline on a stale clock against a champion on a fixed one
  is not a comparison. The corrected ladder replaces the earlier numbers.

## The procedural lesson worth saying out loud
A plausible cause with a plausible mechanism and consistent-looking evidence was
still wrong. What caught it was cheap: build the fix, probe it against the running
system, and check whether the thing you predicted would change actually changed.
It cost 22 conversations and about fifteen minutes, and it prevented a false
finding from reaching a slide — and, worse, a "fix" that would have been credited
with a recovery it did not cause.

---

# FINAL LADDER — corrected clock, zero transport errors

All 600 verification conversations re-run after two faults were found and fixed:
a stale environment clock, and an expired dashboard token that had silently
scored 141 conversations as behavioural failures when they were HTTP 401s.

## Headline
**v3 98/180 → generation 2 160/180 (+63% relative).** Blind 33/60 → **59/60**.
**62 scenarios fixed, 0 broken.** McNemar exact **p ≈ 0**. Guardrail families
40/73 → **63/73**. Words per agent turn 15.9 → 15.6.

| suite (180) | strict | env-conditioned |
|---|---|---|
| v3 BASE | 88 | 98 |
| generation 1 | 135 | 155 |
| **generation 2** | **141** | **160** |

| fresh blind-30 *(generated after the run; no search ever saw it)* | strict | env-cond. |
|---|---|---|
| v3 BASE | 16 | 18 |
| generation 1 | 23 | 27 |
| **generation 2** | **25** | **29** |

Both columns are reported everywhere. Strict demands the literal pinned argument;
env-conditioned credits a pinned date when the agent produced the environment's
value for the same relation, because the channel never delivers the scenario's own
clock to the agent. It applies identically to every version, so no comparison
depends on the choice.

## Per rung
| rung | overall | blind | guardrails | paired | p |
|---|---|---|---|---|---|
| v3 → gen-1 | 98→155 | 33→57 | 40→62 | +59 / −2 | ≈0 |
| gen-1 → gen-2 | 155→160 | 57→59 | 62→63 | +7 / −2 | **0.18** |
| **v3 → gen-2** | **98→160** | **33→59** | **40→63** | **+62 / −0** | **≈0** |

## Two corrections to what was reported earlier
1. **Generation 2 is not worse — it is the champion.** The earlier "gen-2
   regressed, guardrail veto" reading came from 51 of its 180 conversations
   failing on an expired token. On clean data gen-2 dominates on every axis with
   **zero regressions**, and it is what now sits on the draft.
2. **`callback_capture` never regressed.** It reads 11/11 on a correct clock. The
   exemplar-copying diagnosis was falsified by experiment (see the correction
   section above) and the miner was reverted.

## What is claimed, and what is not
- **Claimed:** one strongly-verified improvement cycle, machine lineage
  end-to-end, significant far beyond a pre-measured noise floor (flip rate 2.2%,
  σ₆₀ = 0.82; the blind delta is +26 against a 1.6 threshold), generalising to
  scenarios generated after the fact.
- **Not claimed:** that improvement compounds across generations. gen-1 → gen-2
  is +5 overall at **p = 0.18** — positive and regression-free, but not
  established. The honest sentence is *"a second generation helped slightly and
  broke nothing."*
- **Not yet measured:** voice. Every figure here is the text channel of a voice
  agent. S7 is the transfer test.

---

# ATTRIBUTION — two experiments that answer the obvious challenges

## 1. Did the second candidate component earn its place? (blind 60)
| | passes |
|---|---|
| v3 BASE | 33/60 |
| champion, **instructions only** | 49/60 |
| champion, **both components** | **59/60** |

The second component carries **10 of the 26-pass gain — 38%**. It is load-bearing,
not decorative.

One precision that matters: GEPA evolved that slot into a **rules block**
(`CRITICAL TOOL RULES: every business event MUST have a corresponding tool call…`),
not into richer demonstrations. So the credit belongs to *a separately-optimised
second text component*, not to few-shot demos specifically — and this is a graft of
MIPRO's insight onto GEPA, not the MIPROv2 algorithm. Say it that way.

## 2. Did it learn tool discipline, or the utterance bank's phrasings? (30 scenarios)
Every caller line reworded by Gemini, writing system pinned and verified per line
(**0/131 script flips** after a first attempt drifted 26% into Devanagari and was
rejected). Required actions, accepted dispositions and account values untouched, so
the grading contract is identical and only surface wording moves.

| | original | reworded | Δ |
|---|---|---|---|
| v3 BASE | 18/30 | 17/30 | −1 |
| champion | 29/30 | 26/30 | −3 |

The champion's 3-pass drop is real (above the 1.16 noise threshold), so it is not
perfectly wording-independent. But it **retains +9 of its original +11 advantage —
about 82% of the gain survives complete rewording.** The improvement is mostly
transferable tool discipline, with a modest surface-form component. Reporting the
−3 is what makes the +9 believable.

---

# v4 COMMITTED · evidence staged · S7 preflighted

## The commit
Generation 2 committed as **v4** on `EasyCredit--4e112b0d-9931`, verified by hash
before and after: `667ce12e2626c75e`, 15,347 characters, byte-identical to
`CHAMPION.json`. Nothing was typed into the editor, so the machine-only lineage
holds all the way to the deployed version.

**Caught at the commit boundary:** `.env` still read `SARVAM_APP_VERSION=3`. The
phone and bot-to-bot harnesses read that variable, so the S7 round would have
silently re-tested the *baseline* and concluded the improvement did not transfer.
Now 4, and smoke-tested — asked "maine to pichle hafte hi pay kar diya tha", v4
replied "मैं एक बार check कर लेता हूँ" and called `check_payment_status`, which is
exactly the rule generation 2 added.

## Call evidence retrieved
Three analytics endpoints were found by capturing the console's own traffic:
`unified-report` (one row per interaction), `interactions/{id}/transcript`, and
`interactions/{id}/merged-audio`. All **15 baseline phone calls** came back with
transcripts *and* recordings; the mapping to cards is exact — every known defect
lands on its expected card (P2 on card 11, P3 on 12, P5 on 13), and the tally is
9/15, matching the recorded baseline.

The recordings arrive as WAV despite an `.mp3` name; they are transcoded for the
web. Transcripts are shown as evidence of what was *said* — they never decide
whether a tool ran, which stays with the journal exactly as in every other tier.

## Site
Two new pages inside the Loopline app, both data-driven from the run artifacts:
- `/campaign2.html` — headline, the five-stage architecture, the full ladder,
  family movement, attribution experiments, instrument audit, limits, and a
  **call browser**: a grouped dropdown over all 20 recorded calls with audio,
  verdict pills, the missing-write callout, and the full transcript.
- `/evolution.html` — the prompt diffs, BASE → Gen 1 → Gen 2.

`scripts/export_site_data.py` regenerates every figure from the artifacts and
asserts each one, so a stale artifact fails the build rather than shipping a
wrong number onto a page someone will present from. Contrast measured: body text
12.4:1, lowest element 5.6:1, both themes, no horizontal overflow.

## S7 is preflighted, nothing spent
`scripts/preflight_s7.sh` — champion hash on the committed agent, version pin,
clock freshness, tunnel, tool service, the five EVA records, ElevenLabs caller
config. All green. It prints the run commands and stops there.

**Sequence:** 5 bot-to-bot calls (~25 credits) as the canary, then the 15 phone
cards. The call sheet now carries a per-card **hang-up tally** — defect P6 is the
one thing the text tier cannot measure.
