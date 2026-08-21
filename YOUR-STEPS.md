# What I need from you — exact steps

Everything that can be done without you is done. Three things need your hands or your
authorisation. They must happen in this order: **tools → commit → voice**. Running the
paid voice round against mock tools or a drifted prompt produces a number that looks
like an answer and isn't.

Total time: about 25 minutes of your attention, plus one paid run.

---

## Step 1 — Open a public HTTPS door to the tool service (~5 min)

The service is already running and verified (9/9 checks pass, fail-closed auth, run
isolation, real state mutation, append-only log). It just isn't reachable from the
internet, so Sarvam's tool caller can't hit it.

You have `ssh` and no tunnel binaries installed, so pinggy is the zero-install option.
**Run this in a terminal and leave it open:**

```bash
ssh -p 443 -R0:localhost:8788 a.pinggy.io
```

It prints a URL like `https://abcd-12-34-56-78.a.free.pinggy.link`.

**Paste that URL back to me.** That is all I need for this step — I'll do the
verification against it.

Two notes:
- The free tunnel expires after 60 minutes. If we're mid-run when it dies, just
  re-run the command and send me the new URL.
- Do **not** disable authentication to "make it work". The service is fail-closed by
  design and that property is half the point of the demo.

*Optional hardening:* if you'd rather allowlist, Sarvam's tool caller comes from
`4.213.167.70`.

---

## Step 2 — Put the tool secret into Indus, and let me wire the rest (~10 min)

I generated a 32-byte secret and wrote it to `voice-agent-improvement/.env` as
`LOOPLINE_TOOL_SECRET`. I have deliberately **not** printed it into this conversation,
because a credential pasted into a chat log has to be treated as burned — that is the
exact mistake we're still carrying from last time.

To read it yourself:

```bash
grep LOOPLINE_TOOL_SECRET /Users/Arnav/Claude/Projects/Sarvam/voice-agent-improvement/.env
```

Then, in the Indus builder for **Conversation Agent 6820**:

1. Go to **Tools**.
2. For each of the three tools — `check_payment_status`, `record_promise_to_pay`,
   `schedule_callback` — set auth type to **api_key**, header name
   `X-Loopline-Tool-Key`, and enter the secret through the **masked input** so it is
   stored in workspace Secrets.

**This is the step that failed last time.** A header typed directly into the tool
config does not survive into the test runtime; a workspace Secret reference does.
Sarvam's own docs say the credential is never typed into the tool config.

Once the secret exists as a workspace Secret, tell me — **I can do the rest in the
browser**: endpoints, methods, bodies, the `campaignId → run_id` and
`transactionReference → account_id` mappings, and `save_to_variables` so results come
back into the agent instead of vanishing.

---

## Step 3 — Say go on the paid voice round (~1 hour, ~170 credits)

Only after steps 1 and 2 land, and after I've captured one real tool side effect.

Before I spend anything I will run three pilot calls and show you the audio,
termination reason, transcripts and tool events. You look at those, then say go or
stop. If you say go, I run the frozen 18-record suite against both agents — 36
provider sessions — and the independent gate emits promote, hold, or roll back.

**Check your balances first:** Sarvam credits and ElevenLabs minutes. Estimate is
~170 Sarvam credits based on the ~63 credits the earlier overnight run consumed for
roughly 14 sessions.

A hold or a rollback is a successful outcome and gets presented as one. I am not
going to tune anything to force a green number.

---

## One decision, whenever you're ready

The approved prompt needs to go back into the Indus draft, replacing the copilot's
drift. I can paste it in the browser — but committing an immutable version is
irreversible, so I'll show you the exact diff and wait for your yes before committing.

Say the word and I'll stage it now so it's ready the moment the tools are wired.

---

## What I'm doing meanwhile

Not blocked on any of the above, and continuing now:

- the episodic-memory layer, so confirmed failures become durable lessons the next
  cycle inherits;
- the turn-level verifier for high-stakes turns — amounts, dates, commitments;
- the 90-day plan, the outcome-join contract, and the scale architecture.
