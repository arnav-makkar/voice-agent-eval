# Voice round — what you're approving

Read this, then say go or stop. Nothing is spent until you do.

---

## 1. What metrics we actually have

You asked whether we have EVA-A / EVA-X. **Yes — the taxonomy is implemented. But in
text mode five of thirteen components come back `null`, not scored**, because they
need audio. The evaluator writes null with a reason rather than substituting a proxy.

| Component | Text mode (today) | Live voice (this round) |
|---|---|---|
| **EVA-A** Task completion | deterministic ✓ | deterministic ✓ |
| **EVA-A** Faithfulness | LLM judge ✓ | LLM judge ✓ |
| **EVA-A** Agent speech fidelity | **null** — `agent_audio_asr_required` | audio judge ✓ |
| **EVA-X** Conciseness | code metric ✓ | LLM judge ✓ |
| **EVA-X** Conversation progression | LLM judge ✓ | LLM judge ✓ |
| **EVA-X** Turn taking | **null** — needs duplex timing | deterministic ✓ |
| **Validation** Conversation finished | deterministic ✓ | deterministic ✓ |
| **Validation** Caller behavioural fidelity | deterministic ✓ | LLM judge ✓ |
| **Validation** Caller speech fidelity | **null** | audio judge ✓ |
| **Diagnostic** Tool call validity | deterministic ✓ | deterministic ✓ |
| **Diagnostic** Response speed | harness timing | provider timing ✓ |
| **Diagnostic** Key-entity transcription | **null** | LLM judge ✓ |
| **Diagnostic** STT word error rate | **null** | deterministic ✓ |

**This is the argument for the round.** The five blanks are exactly where voice agents
fail — did it say the amount correctly, did it talk over the caller, did the date
survive the audio path. We currently cannot answer any of that at scale. One live call
has the full set; eighteen would give us both arms.

---

## 2. What version we are testing

**Baseline arm — the agent as deployed.** Indus app version 12. This is what has been
answering calls, and what produced the 20 real discovery calls.

**Candidate arm — the approved agent.** `agent/candidates/v15-firm-today.md`,
sha256 `732d216b3a75bcb2d6424946cf935dfd1584d723f31020bb746908431dad90e3`.

⚠️ **This is not yet what is in your Indus draft.** The draft currently holds the
copilot's drifted rewrite, which I registered as a separate candidate and scored at
22/30 against the approved agent's 30/30. Before this round runs, the approved prompt
has to go back in and be committed as an immutable version. I'll stage it and show you
the exact diff; committing is your call.

**If we run against the drifted draft, the result is uninterpretable** — we would be
measuring a prompt that never passed the sealed test.

---

## 3. Is this benchmarking or final testing?

**Neither, exactly. It is a transfer test.**

We already have the baseline (text, 30 scenarios) and the improvement result (sealed,
12 cases). The open question is narrower and more interesting:

> A repair was designed and validated in text. Does it survive the audio channel?

That is not guaranteed. Text-mode evaluation cannot see whether the agent talks over
the caller, whether "20-08-2026" survives TTS and STT, or whether a language switch
degrades entity accuracy. **The honest expectation is that some of the text-mode gain
does not transfer.** That result would be worth presenting.

It is also the **final gate** before any promote decision. The release controller reads
the paired result and emits promote, hold, or roll back. It will not be re-run to get a
nicer answer.

---

## 4. Yes — these are bot-to-bot, and yes, they showcase like EVA

**Architecture**, identical to the one validated run:

```
ElevenLabs realtime agent "Arnav"      ← the caller, independent of what we're testing
        ⇅ live bidirectional audio
project-owned EVA assistant adapter
        ⇅ Samvaad WebSocket
deployed Sarvam Indus agent "Shubh"    ← the system under test, complete and untouched
```

The caller is a real realtime voice agent with a hidden goal and a persona, not a
script and not a TTS playback. Shubh is the actual deployed agent — we are not
reconstructing it from separate STT/LLM/TTS parts.

**Every record preserves**: mixed and per-speaker audio, transcript, Samvaad events,
tool calls, initial and final state, provider termination reason, per-turn latency,
and the full EVA score set. That is exactly the material the episode gallery already
renders — the difference is it will be real audio, for both arms, with the five blank
metrics filled in.

---

## 5. The suite — 18 records, frozen

Frozen under evaluator `evaluation-metrics.v3/loopline-eva-adapter.v1/samvaad-duplex.v10`,
bundle sha `35553ac8…`. Records and trial counts are identical across both arms.

**12 core scenarios** spanning **Hindi, Hinglish, English and Punjabi**: pay-now,
future promise, callback capture, already-paid, dispute, wrong number, unsupported
channel, credential guardrail, language switch.

**6 acoustic-risk scenarios** — background noise ×2, low gain ×2, packet loss, jitter.
These exist because a text-mode win that evaporates under noise is not a win.

---

## 6. Tools — yes, and here is the exact status

**The tool path is now live and verified through your tunnel.** I ran the full check
against `https://bkrcf-106-219-122-250.free.pinggy.net` and all nine passed:

- unauthenticated call → **401**, fails closed
- authenticated call → **200**, `recorded: true`
- state genuinely moved: `promise_to_pay_date` null → `20-08-2026`
- wrong account → **409**; unknown run → **404**
- every call landed in an append-only log

**4 of the 18 records require a real tool call:**

| Record | Scenario | Tool it must call |
|---|---|---|
| EMI-VOICE-002 | future promise | `record_promise_to_pay` |
| EMI-VOICE-003 | callback capture | `schedule_callback` |
| EMI-VOICE-009 | language switch (Punjabi) | `record_promise_to_pay` |
| EMI-VOICE-018 | language switch + low gain | `record_promise_to_pay` |

**Still to do before the round:** you saved the secret — thank you, that was the step
that failed last time. What remains is the endpoint URLs, request bodies, the
`campaignId → run_id` and `transactionReference → account_id` mappings, and
`save_to_variables`. **I can do all of that in the browser.** Say the word.

Until one of those four records actually fires a tool through Indus, we still cannot
claim live execution truth — the service being reachable is not the same as the
platform using it.

---

## 7. The ElevenLabs plan

**What it costs.** 18 records × 2 arms = **36 ElevenLabs sessions**, one per record,
plus 3 pilot sessions first. Observed duration on the validated run was ~47s; budget
~60–90s each. **Roughly 40–60 minutes of realtime agent time total.**

On the free tier that is likely to be tight. Check your balance — if it is short, the
cheapest sufficient paid tier covers it comfortably. This is a one-time spend, not
recurring.

**What it costs on Sarvam.** ~36 Samvaad sessions. Estimated **~150–170 credits**,
extrapolated from the ~63 credits an earlier overnight run consumed for ~14 sessions.
Please confirm your balance before I start.

**Guardrails already in the runner** — I am not removing these:
- explicit `--max-sessions` cap, and it refuses to exceed it
- explicit `--confirm-live-suite` flag; nothing runs by accident
- **no automatic paid retries** on failure
- provider failures are recorded as infrastructure-invalid and excluded from agent
  scoring rather than counted as agent failures

**Caller identity** is a provisioned ElevenLabs agent named **Arnav**, Indian male
voice, with a hidden EMI goal and a low-attention persona. It already exists from the
validated run — no new provisioning needed.

---

## 8. What I will do, in order

1. **Three pilots first** — one straightforward pay-now, one tool-dependent, one
   language/experience risk. ~3 sessions.
2. **I stop and show you** the audio, transcripts, termination reasons and tool events.
3. **You say go or stop.** If transport or evaluator problems appear, I fix those and
   re-run the pilots. If the *agent* behaves badly, that is preserved as a result — I
   do not fix the agent to make the round look better.
4. Only then, the 18 records on the baseline arm and the 18 on the candidate arm.
5. The independent comparator emits promote / hold / roll back, and it is published
   whichever way it lands.

**Both promotion routes were declared before any of this:** more matched task wins, or
the same wins with materially fewer integrity and experience defects. The second is
reported as quality improvement, never as a lift in task success.

---

## What I need from you to start

1. **Go/no-go** on the ~36 sessions.
2. **Confirm balances** — Sarvam credits and ElevenLabs minutes.
3. **Let me wire the tool endpoints** in the browser (you've done the secret).
4. **Approve restoring the approved prompt** into the Indus draft — I'll show the diff
   before committing.

The tunnel expires 60 minutes after you started it. If it dies, re-run the ssh command
and send me the new URL; nothing else is affected.
