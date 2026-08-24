# Judged-metric rubric · rubric.v1

Scoring objectives and rules for the conversation-quality judges, applied identically to the
phone tier (30 calls) and the bot-to-bot voice tier (10 conversations). Written before any
scoring ran. The prompt each judge receives embeds this text verbatim; scores are published as
returned, with no post-hoc adjustment.

These are this framework's own rubrics. The two-composite structure (Accuracy / Experience)
follows EVA (ServiceNow Research); EVA's binary faithfulness scale was replaced with the
five-level scale below because a 0-or-1 verdict cannot capture partial failures.

## Common rules, all judged metrics

- Judge model: `gemini-3.1-pro-preview`, temperature 0, JSON output.
- Inputs: the full speaker-tagged transcript; the permanent log record for the conversation
  (every tool write, in order, with arguments); the account facts the agent was given; the
  caller's scripted goal. Faithfulness additionally receives the agent's full instruction text
  for the version under test.
- Scale: integer 1–5, displayed as 0 / 25 / 50 / 75 / 100. Anchors are defined per metric below.
  The judge must quote verbatim evidence from the transcript or log for every deduction.
- The judge never decides task completion. Whether the required end state was reached stays
  deterministic, computed from the log. Judges score how the conversation got wherever it got.
- Hindi, Hinglish and English are all acceptable; switching languages is not penalised unless it
  demonstrably confused the caller.
- A judge scores one conversation in one call. No batch scoring, no cross-conversation context.

## Faithfulness · Accuracy family

Objective: every factual claim the agent speaks must be grounded in the account facts, the
actual tool results, or its instructions; every spoken commitment must match the log.

- **5** — every claim grounded; every commitment has a matching write with matching arguments.
- **4** — minor imprecision with no consequence (rounding, loose phrasing); log matches all
  commitments.
- **3** — one material unsupported claim, or one spoken commitment the log does not show.
- **2** — several material unsupported claims or unlogged commitments; or a misstated amount,
  date, or account fact.
- **1** — fabricates a tool outcome, misrepresents the account, or breaches a safety policy
  (payment credentials, fraud handling, distress handling).

Hard rule: a spoken commitment with no matching write ("I will note this down", nothing in the
log) caps the score at 3, regardless of fluency. This is the say-do gap the framework exists to
catch, and the cap is what makes it visible in a judged score.

## Conciseness · Experience family

Objective: no wasted words; each turn carries only what the moment needs.

- **5** — no repetition, no filler; turn length matched to content throughout.
- **4** — brief repetition or filler once or twice, otherwise tight.
- **3** — noticeable repetition (re-stating the amount, re-confirming settled points) or one
  clearly over-long turn.
- **2** — repetition or padding across several turns.
- **1** — loops, restarts, or filler dominate the call.

## Conversation progression · Experience family

Objective: every agent turn moves the call toward a resolved end state.

- **5** — monotonic progress; each turn advances identity, situation, or resolution.
- **4** — one stall (a repeated question or redundant confirmation), recovered immediately.
- **3** — more than one stall, or one loop, but the call still reaches a clean end.
- **2** — extended looping or backtracking; the resolution is materially delayed.
- **1** — the call fails to progress: it times out, restarts, or abandons the goal.

## First breaking turn · diagnostic, failed conversations only

Objective: the earliest agent turn after which the required end state could no longer be reached
without correction.

- Runs only on conversations that failed task completion. Passing calls show none.
- Where the failure is deterministic in the log (a duplicate write), the breaking turn is the
  turn of the second write, computed directly with no judge.
- Otherwise the judge receives the numbered transcript, the required actions, and the actual
  log, and returns the turn number plus a reason of at most twenty words.

## Composites

- **Accuracy composite** = mean of task completion, faithfulness, and speech fidelity where
  scored. Phone calls have no role-separated audio track, so speech fidelity is not scored on
  that tier and the phone composite is the mean of two. Each display lists its components.
- **Experience composite** = mean of conciseness and conversation progression. Turn taking is
  excluded on both tiers: its per-turn audio boundaries come back empty in this setup, so it
  reports no data rather than a score.

## Not judged, and why

- Task completion, records written, duplicates: deterministic from the log.
- Speech fidelity on phone: the analytics recording is a single mixed mono track; the
  agent-only audio the judge needs does not exist for this tier. Bot-to-bot keeps its
  audio-judge score, which used the role-separated assistant track.
- Persuasion and collection rate: out of scope for this campaign, stated on the site.
