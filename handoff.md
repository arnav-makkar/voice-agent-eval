# Claude Code Handoff: Loopline — Self-Improving Voice-Agent Framework

Last reconciled: **2026-08-21, Asia/Kolkata**

Primary workspace: `/Users/Arnav/Claude/Projects/Sarvam`

Implementation workspace: `/Users/Arnav/Claude/Projects/Sarvam/voice-agent-improvement`

Dashboard workspace: `/Users/Arnav/Claude/Projects/Sarvam/dashboard`

Primary plan: `/Users/Arnav/Claude/Projects/Sarvam/FINAL-INTERVIEW-DECISION.html`

Audience: Claude Code or another coding agent taking over the project without access to the original chat history.

This file is intentionally long, explicit, and machine-oriented. The update below is the current source of truth; later sections preserve the earlier implementation lineage.

## 2026-08-21 final takeover update

### Current decision

**PASS the sealed text improvement. HOLD the live voice release.**

- The frozen stateful text final remains **5/12 → 9/12**, with four repaired cases and zero observed task regression. This is the headline result, not the in-sample 30/30.
- The selected prompt was committed in Indus. Authenticated Sarvam-originated tool requests reached the run-scoped service and produced real state mutation.
- A three-call v16 live pilot produced **1/3 task passes**, **1/3 EVA-A passes**, **0/3 EVA-X passes**, and EVA overall mean **0.4417**.
- A targeted v18 repair rerun produced only **one evaluator-valid call out of three**. The valid future-PTP case preserved its task pass and one exact tool write, but still failed EVA-X. One pay-now trial timed out at the WebSocket layer; the Punjabi PTP trial was simulator-invalid and still missed its required write.
- The 18-case matched live suite was deliberately not run. Its pilot advance rule failed. This is a complete HOLD decision, not unfinished analysis and not a production promotion.

Machine decision: `voice-agent-improvement/artifacts/framework/emi/live_voice_pilot_decision.json`.

### What changed after the earlier handoff

1. Owner review of all 20 discovery labels is versioned, and the owner confirmed the previously exposed key was rotated.
2. Indus deployment manifests now preserve v15 prompt identity, v16 live tool configuration and the v18 pilot repair.
3. The three Indus tools use distinct runtime mappings and an authenticated workspace secret; `record_promise_to_pay` executed during live bot-to-bot calls.
4. The EVA–Samvaad adapter now rejects `NA`, `N/A`, empty and null sentinels instead of projecting them as false state mutations.
5. Evaluator **v11** freezes the post-pilot adapter/tool changes. V10 is unchanged and remains the pilot lineage.
6. Loopline now includes a prospective voice-pilot section with exact denominators, a HOLD decision, three replayable recordings, tool-effect evidence and proven/unproven repair ledgers.
7. Latest verification passes **82 Python tests**, dashboard lint, four render tests, production build, freeze checks, final-protocol checks and secret scan.

### Current claim boundary

> I built and deployed a governed failure-to-release loop around a Sarvam Indus voice agent. It improved exact task completion on a sealed stateful text final, proved authenticated live tool mutation, and ran prospective realtime bot-to-bot pilots. The live gate correctly held the candidate because the repair round was not reliable or complete. I do not claim live lift, settled-cash lift, or production readiness.

### Demo sequence

1. Run `cd dashboard && npm run dev`, then open `http://localhost:3000`.
2. Start with **5/12 → 9/12**, immediately state that 30/30 is in-sample and not the headline.
3. Show the three independent engines: Evaluation, Improvement, Release.
4. In Episodes, show at least five preserved cases; use the promise-write comparison, ledger contradiction, callback, Punjabi and rejected-GEPA cases.
5. In Voice pilot, play the PTP recording, show its exact tool/state write, then show the Punjabi miss and the transport-invalid call.
6. Close on **PASS TEXT · HOLD VOICE PILOT** and the 30/60/90-day production plan.

### Only remaining production gate

Fix caller-language validation, make opening/tool-before-claim behavior workflow-enforceable, and repeat the same three live pilots. Run the 18-case matched suite only after all three are evaluator-valid and every required effect passes.

---

## 0. How to use this handoff

### 0.1 Source-of-truth precedence

When files disagree, use this order:

1. Immutable or hash-linked machine artifacts under `voice-agent-improvement/artifacts/`.
2. `voice-agent-improvement/artifacts/framework/completion_audit.json` for plan status.
3. `voice-agent-improvement/artifacts/framework/verification/latest.json` for test/build status.
4. `voice-agent-improvement/artifacts/framework/execution_manifest.json` for the current architecture and claim boundary.
5. `voice-agent-improvement/README.md` for operational commands.
6. `FINAL-INTERVIEW-DECISION.html` for the current presentation narrative.
7. This handoff.
8. Older planning HTMLs and markdown files, which are historical design lineage rather than current truth.

Never silently rewrite historical evidence to make it agree with a newer evaluator or presentation. Create a new version and disclose the supersession.

### 0.2 Immediate rules for Claude Code

1. Do not print `.env`, API keys, phone numbers, signed recording URLs, or raw secrets.
2. Do not place a paid Sarvam or ElevenLabs call without explicit action-time authorization from Arnav.
3. Do not deploy, commit, or mutate the Indus agent without explicit authorization.
4. Do not edit the frozen V10 evaluator or frozen matched suite and continue to cite their current hashes.
5. Do not tune on or regenerate the sealed fresh final.
6. Do not claim matched live V15 lift, live tool execution, collected cash, or production-scale validation. None exists yet.
7. Do not call the 20 calls “gold.” Their labels are provisional until Arnav reviews them.
8. Do not treat the old 200 generated rows as independent held-out proof. They are development diagnostics.
9. Do not call GEPA the self-improving framework. It is one repair generator inside the improvement engine.
10. Keep the active synthetic caller name exactly **Arnav**, not “Arnav Dhavala.” Historical raw artifacts that contain the old full name remain immutable.
11. Preserve negative experiments. A rejected candidate is evidence that the gate works.
12. The workspace root is not currently a Git repository. Do not assume Git history exists.

### 0.3 One-sentence project status

Loopline is a working, locally verified evaluation–diagnosis–improvement–release framework around a real Sarvam Indus voice agent; text-mode candidate improvement and one genuine realtime EVA-to-Samvaad evaluation are proven, while live tool execution and matched V12/V15 voice improvement remain open gates.

---

## 1. Executive summary

### 1.1 What Arnav was asked to build

The original assignment was to design and implement a **self-improving voice-agent system**, with particular emphasis on:

- voice-agent evaluation;
- identifying where conversations begin to fail;
- converting failures into durable tests;
- proposing improvements;
- evaluating improvements fairly;
- showing a repeatable learning loop rather than a one-off prompt rewrite;
- producing an interview-ready PM/CXO narrative and demo.

The validation domain is EMI recovery. The architecture is intentionally domain-configurable so that hospital customer service, banking support, insurance, appointments, or other conversational workflows can provide their own domain pack.

### 1.2 The final architecture

The project deliberately separates three responsibilities:

1. **Evaluation Engine**
   - Runs versioned scenarios.
   - Captures conversation, audio, events, tool calls, and state.
   - Validates the simulated caller.
   - Scores deterministic task truth first.
   - Uses semantic judges only for qualities that cannot be verified deterministically.
   - Finds the first observable breaking event.

2. **Improvement Engine**
   - Consumes failure packets from development evidence.
   - Assigns failures to prompt, extractor, tool, workflow, knowledge, model/runtime, voice/channel, policy, or human-review owners.
   - Runs manual prompt repair, GEPA Optimize Anything, extractor repair, or other bounded repair arms.
   - Produces versioned candidates and diffs, not release claims.

3. **Release Controller**
   - Freezes evaluator, scenarios, state fixtures, thresholds, and candidates.
   - Compares baseline and candidate per case.
   - Prevents an aggregate score from hiding a severe regression.
   - Runs a once-only group-separated final.
   - Requires matched real voice evidence before live promotion.
   - Emits promote, hold, or rollback.

### 1.3 Current evidence in one table

| Evidence layer | Status | What it proves | What it does not prove |
|---|---|---|---|
| 20 real V12 Indus calls | Preserved | Real voice-system discovery and failure taxonomy seed | Gold labels, causal lift, customer-population performance |
| 200 static next-turn cases | Preserved but demoted | Cheap development screening and regression debugging | Independent held-out or voice improvement |
| 30 stateful scenarios | Complete | Multi-turn task/state/action evaluation with fresh state | Live audio performance |
| Matched V12/V15 text comparison | Complete | Candidate repairs under deterministic state/action evaluation | Voice TSR |
| 12-case sealed text final | Complete | V12 5/12 to V15 9/12, four repairs, zero observed task regressions | Statistical generalization or production lift |
| Six-condition acoustic diagnostic | Complete, baseline only | Component-level V12 behavior under audio risks | Matched candidate lift |
| One EVA–Samvaad live run | Complete | Genuine realtime ElevenLabs caller ↔ Samvaad agent, with audio and EVA scores | Reliability or V15 improvement |
| Live Indus tool side effect | Missing | — | Tool-selection and say/do execution truth in production runtime |
| Frozen matched V12/V15 live suite | Protocol complete; execution missing | — | Final voice promote/hold/rollback decision |

### 1.4 Current plan status

The machine audit currently reports:

```text
complete                         19
documented_fallback               1
external_blocked                  1
external_pending                  4
not_required_for_current_gate     1
owner_confirmation_required       1
partial                           1
pending_on_matched_voice          1
```

The four binding open gates are:

1. Arnav reviews and versions the 20 provisional discovery labels and confirms the exposed Sarvam key was rotated.
2. A secure public tool route works from deployed Indus and one real tool side effect is captured.
3. V15 is committed as an exact immutable Indus version.
4. The frozen matched V12/V15 live suite runs and the independent gate emits promote, hold, or rollback.

### 1.5 Current defensible claim

> I built a domain-configurable failure-to-release control plane around a real Sarvam Indus voice agent and adapted EVA for one validated realtime bot-to-bot evaluation. The candidate passed a sealed text final, but remains held until a real tool effect and matched V12/V15 voice suite pass the frozen gate.

### 1.6 Claims that are not currently supported

Do not say:

- “V15 improved live voice TSR.”
- “The agent collected more money.”
- “The tool path works live in Indus.”
- “The 20 calls are human gold.”
- “The 200 cases are independent held-out evidence.”
- “EVA proved reliability from one run.”
- “The system can directly process one million SBI or LIC calls with minor changes.”
- “GEPA alone made the voice agent self-improving.”
- “The system autonomously modifies production.”
- “The candidate is production-ready.”

---

## 2. Verbatim final status answer included at Arnav’s request

The following is the final status explanation given immediately before this handoff. Preserve it as the concise human-facing summary.

> The framework is substantially built, but the final live improvement proof is not complete. The audit records **19 completed items and four binding gates remaining**.
>
> ## Phase status
>
> | Phase | Status | What is done / missing |
> |---|---|---|
> | P0 — Truth repair | Partial | Strict regression gates, evidence cleanup and 200-case diagnostic library are done. Your review of the 20 discovery labels and API-key rotation remain. |
> | P1 — EVA/Indus integration | Partial | Real ElevenLabs Arnav ↔ Samvaad duplex audio works. A real deployed Indus tool side effect is still missing. |
> | P2 — EMI evaluation world | Complete | 30 stateful scenarios, three tools, isolated SQLite state, assertions and simulator validation are implemented. |
> | P3 — Evaluation | Partial | EVA-inspired evaluator V10, metrics and one fully scored live run exist. Owner calibration and repeated matched voice evidence remain. |
> | P4 — Improvement | Complete locally | Manual prompt repair, GEPA, extractor repair, failure routing and MLflow lineage are implemented. |
> | P5 — Re-evaluation/release | Partial | Matched text evaluation and sealed fresh-final test passed. Matched V12/V15 voice evaluation has not run. |
> | P6 — Loopline UI | Built | Production build passes and the valid live call is replayable. Tool and reliability panels await real evidence. |
>
> ## What is completed
>
> - Evaluation, improvement and release control are separated.
> - 20 real V12 calls are preserved as discovery evidence.
> - The 200 generated cases are correctly treated as development diagnostics—not final proof.
> - EVA, τ-bench and Riley references are pinned with licensing records.
> - A genuine live audio-native bot-to-bot path works: `ElevenLabs Arnav ⇄ Samvaad Shubh`.
> - Audio, transcripts, events, latency, first failure and EVA scores are captured.
> - The current prospective evaluator is frozen as V10.
> - 30 stateful EMI scenarios cover commitment, refusal, callback, dispute, wrong number, language switching and other cases.
> - Three run-isolated tools are implemented and tested: `check_payment_status`, `record_promise_to_pay`, `schedule_callback`.
> - Manual, GEPA and extractor improvement arms have been executed.
> - Failed candidates and experiment lineage are retained in MLflow.
> - V12 and V15 were compared on identical text-mode scenarios.
> - A sealed 12-case text final improved from **5/12 to 9/12**, with no observed task regression.
> - Strict gates prevent aggregate improvement from hiding severe per-case regressions.
> - Loopline builds successfully.
> - Latest verification passes: **79 Python tests**, dashboard lint, dashboard tests, production build, hashes and secret scan.
>
> ## The four binding gates left
>
> 1. **Own the baseline labels**
>
>    Review and approve the 20 provisional discovery labels and their first-failure turns. Until then, evaluator calibration is against Codex-assisted labels—not human gold.
>
>    Also confirm that the previously exposed Sarvam API key was rotated.
>
> 2. **Capture one real tool execution**
>
>    Expose the run-scoped tool service through authenticated HTTPS and attach it to Indus. Capture one trace containing tool selected, arguments, result, timestamp, state before and after, and spoken claim versus actual action.
>
>    The backend exists, but Indus previously failed to propagate the configured credential.
>
> 3. **Commit V15 immutably in Indus**
>
>    Commit the selected V15 prompt as an exact agent version and record its version plus prompt hash `732d216b…`. Do not make further prompt changes after this.
>
> 4. **Run prospective matched voice evaluation**
>
>    First run **three pilot realtime scenarios**. Inspect audio, termination, transcripts and tool events.
>
>    If those pass, run the frozen 18-scenario protocol against both V12 and V15 under identical conditions—36 provider sessions total. The release controller then emits promote, hold or roll back.
>
> ## Current honest claim
>
> You can say:
>
> “I built and locally validated the complete evaluation, diagnosis, improvement and release-control framework around a real Sarvam Indus agent. I also proved one realtime EVA-to-Samvaad bot-to-bot evaluation. The candidate passed sealed text evaluation, but final live promotion remains gated on a real tool effect and matched V12/V15 voice evidence.”
>
> You cannot yet claim that V15 improved live voice TSR.

---

## 3. Product objective and metric contract

### 3.1 Framework objective

Build a reusable, governed system that can take production or controlled conversational-agent traces and answer:

1. What business task was supposed to happen?
2. Was the caller/simulator valid?
3. Did the conversation complete the task truthfully?
4. Did required tool effects actually happen?
5. Did the agent say anything inconsistent with execution state?
6. What was the first observable breaking event?
7. Which component owns that failure?
8. Which bounded repair should be attempted?
9. Did the candidate improve the same tasks without new severe regressions?
10. Should a human promote, hold, or roll back the candidate?

The framework is not autonomous production mutation. “Self-improving” means a recurring, instrumented, versioned, human-gated learning loop.

### 3.2 EMI domain objective

For answered, intended, eligible EMI-recovery calls, maximize the share of callers who explicitly agree to open the official EasyCredit app and pay now.

Primary success examples:

- “I will open the app and pay now.”
- “Abhi EasyCredit app se payment karta hoon.”
- Equivalent explicit Hindi, Hinglish, English, or Punjabi present-tense commitment.

Not primary success:

- “I’ll check.”
- “I’ll try.”
- “Maybe later.”
- A callback request.
- A future payment date.
- A vague “okay.”
- A payment-completion claim without ledger/tool evidence.

Correct non-primary terminal outcomes remain valid task outcomes:

- `payment_ready`
- `ptp_today`
- `fptp`
- `callback`
- `rtp`
- `already_paid`
- `dispute`
- `wrong_number`
- `alternate_number`
- `acknowledged`
- `escalation`
- `call_disconnected`

### 3.3 Denominator

No-answer/connect rate is outside the agent-controlled TSR. The primary denominator is answered, intended, eligible callers who can substantively engage.

This decision was explicit because the working assumption is that many recipients are uninterested and may not answer. The agent must be judged on what it controls after connection, not carrier/connectivity behavior.

### 3.4 Business proxy boundary

The MVP observes **verbal pay-now commitment**, not actual cash settlement. A future production system needs a payment-ledger or CRM outcome join before claiming collected-payment lift.

### 3.5 Metric hierarchy

Accuracy / task truth:

- scenario-specific task success;
- exact disposition;
- expected terminal state;
- required action completion;
- forbidden behavior;
- amount/date/entity accuracy;
- tool name, arguments, result, order, and state mutation;
- spoken claim versus execution truth.

Experience:

- directness;
- opening length;
- conciseness;
- progression;
- redundant turns;
- caller burden;
- language adaptation;
- interruption recovery;
- dead air, overlap, and response timing.

Reliability:

- `pass@1` for typical performance;
- `pass@k` for whether any of repeated attempts can succeed;
- `pass^k` for consistent success across all repeated attempts;
- matched acoustic-condition slices.

Guardrails:

- no new P0 safety issue;
- no new integrity violation;
- no unsupported payment/action claim;
- no terminal-state regression;
- no preserved-win regression;
- no aggregate compensation for a severe case failure.

### 3.6 Two valid promotion routes

The controlled V12 voice baseline already had a ceiling problem: nine explicit commitments among ten eligible calls. Therefore a live candidate is not required to produce a numerically higher commitment count to be useful.

Route A — business-win improvement:

- more exact matched task wins than V12;
- zero new P0;
- no safety/integrity regression;
- protected terminal states;
- acceptable experience.

Route B — quality improvement under a ceiling:

- exact task-win count is preserved;
- materially fewer integrity, repetition, or experience failures;
- zero new P0;
- described as task non-degradation plus quality improvement, never as TSR lift.

---

## 4. Case-agnostic architecture

### 4.1 Closed loop

```text
Real or simulated interactions
        ↓
Immutable/redacted traces + run_id + versions
        ↓
Scenario/caller validity gate
        ↓
Deterministic task + state + tool + guardrail truth
        ↓
Secondary semantic and voice-quality evaluation
        ↓
First breaking event + failure family + component owner
        ↓
Failure-derived permanent development/regression tests
        ↓
Repair router
   ├── manual prompt
   ├── GEPA prompt search
   ├── extractor repair
   ├── tool contract repair
   ├── workflow/state-machine repair
   ├── knowledge/policy repair
   ├── model/runtime repair
   └── voice/channel repair
        ↓
Versioned candidate bundle + hypothesis + exact diff
        ↓
Same frozen evaluator and matched scenarios
        ↓
Per-case release gate + once-only fresh final
        ↓
Matched live voice canary
        ↓
PROMOTE / HOLD / ROLLBACK
        ↓
New production traces begin the next cycle
```

### 4.2 Portability boundary: the domain pack

The core framework owns:

- canonical trace schema;
- evaluator interfaces;
- validity rules;
- severity policy;
- first-break representation;
- component router;
- repair registry;
- experiment lineage;
- freeze manifests;
- release record;
- dashboard contracts;
- monitoring and rollback concepts.

A domain pack supplies:

- business task and denominator;
- caller goals/personas;
- account or workflow state;
- allowed/forbidden transitions;
- tools and schemas;
- policy and compliance rules;
- terminal outcomes;
- languages and channel-specific risks;
- deterministic assertions;
- business-outcome join contract.

The active pack is `voice-agent-improvement/framework/domain_packs/emi.json`. A hospital appointment pack exists as a schema portability smoke test at `voice-agent-improvement/framework/domain_packs/hospital_appointments.json`; it is not performance validation.

### 4.3 Why evaluation and improvement must stay separate

Earlier thinking mixed “generate transcripts, optimize a prompt, regenerate transcripts, show a higher score.” That is not a defensible self-improvement system because the optimizer can accidentally redefine the test.

The final design enforces:

- evaluator freeze during candidate comparison;
- scenario freeze;
- prompt/candidate hash;
- independent release controller;
- final-set seal and access log;
- evaluator changes as separately versioned work;
- LLM judges as secondary where deterministic truth exists.

### 4.4 Why GEPA is only one box

GEPA can propose prompt text. It cannot:

- ingest calls;
- define business truth;
- validate the simulator;
- create tool state;
- prove a tool effect;
- decide whether a failure is prompt-owned;
- repair extractors or workflows;
- perform matched voice evaluation;
- approve release;
- measure collected cash;
- roll back production.

Therefore GEPA is retained as a technically substantive prompt-search arm, while Loopline remains the actual framework.

---

## 5. EMI agent and platform context

### 5.1 Sarvam identifiers that are safe to retain

- Organization ID: `019fe148-1997-7cc7-bb7a-8029929d4008`
- Workspace ID: `019fe148-199b-787e-b8d7-b0c2d4e6acda`
- Agent/app ID: `Conversatio-87b9b435-b466`
- Sarvam Voice Agents API base: `https://apps.sarvam.ai/api`
- Authentication header: `X-API-Key`

Connection IDs, phone numbers, API keys, and secrets must remain in `.env` and must not be copied here.

### 5.2 Agent-under-test identity

- Agent name/voice persona: **Shubh**.
- Platform: Sarvam Indus / Samvaad Voice Agents.
- Validation domain: EasyCredit EMI recovery.
- Product: Samsung TV, not a fridge.
- Retail context: fictional EasyCredit/Croma scenario.
- Caller/simulator identity: **Arnav** only.
- Languages: Hindi, Hinglish, English, and Punjabi adaptation.

### 5.3 Prompt/product decisions from real-call observation

The final prompt direction was shaped by actual calls:

- The first message must be short.
- Shubh should identify himself and EasyCredit, mention the Samsung TV EMI, and get to the direct ask quickly.
- Do not read the complete TV specification. “Samsung TV” is enough.
- Avoid saying “4K,” which the voice system pronounced as “four kelvin.”
- Do not add DOB, OTP, reference-number, or lengthy customer-verification flows to this controlled experiment.
- Do not ask for OTP, UPI PIN, card number, CVV, or banking password.
- A clear pay-now commitment is terminal; acknowledge once and close.
- Do not reconfirm the same commitment.
- “I will check/try” is not a commitment.
- Future promises and callbacks require the correct outcome and tool/state path.
- Trust objections should route the user to the official app, without inventing a website, link, or transfer route.
- Switch language by the next substantive turn when the caller consistently uses English or Punjabi.
- The caller is assumed uninterested, so every extra turn has a cost.

### 5.4 Input-variable contract seen in Indus

The project has used or discussed these fictional input variables:

```text
autopayStatus
campaignId
currentDate
customerCareNumber
cutoffDate
daysPastDue
downPaymentAmount
dpdBucket
dueDate
emiAmount
emiNumber
financedAmount
fraudHelplineNumber
lateChargeAmount
lenderName
merchantName
orderIdMasked
outstandingAmount
paymentLinkSent
productName
purchaseAmount
purchaseChannel
purchaseCity
purchaseDate
purchaseTime
remainingEmiCount
retailerName
supportDeskName
supportHours
supportRoute
supportSla
timezone
tomorrowDate
totalEmiCount
transactionReference
userName
verificationReferenceLast4
```

For the tool bridge:

- `campaignId` is mapped to evaluation `run_id`.
- `transactionReference` is mapped to evaluation `account_id`.

Use the Indus builder’s actual variable picker. Do not invent template syntax.

### 5.5 Output-variable contract seen in Indus

```text
callbackDateTime
callbackPreferredDate
callbackPreferredTime
callSummary
disposition
disputeReason
escalationComment
escalationReason
identityConfirmed
promisedToPayDate
userUpdatedNumber
```

The known allowed disposition set is:

```text
escalation
alternate_number
wrong_number
dispute
payment_ready
ptp_today
fptp
callback
rtp
already_paid
acknowledged
call_disconnected
```

The early invalid `fraud_claim` disposition was an extractor/config issue, not a prompt issue. This separation is an important PM/product decision.

### 5.6 Version naming

- V12: deployed baseline used for the real-call corpus and the preserved live EVA run.
- V13: manual stateful repair arm; rejected.
- V14: terminal-discipline repair arm; rejected.
- GEPA finalist: real Optimize Anything prompt-search arm; rejected by strict gate.
- V15: selected offline/manual candidate at `agent/candidates/v15-firm-today.md`; must still be committed immutably in Indus.

The V15 prompt SHA-256 used by the final text experiments is:

```text
732d216b3a75bcb2d6424946cf935dfd1584d723f31020bb746908431dad90e3
```

Do not paste a modified prompt and still call it this V15 candidate.

---

## 6. Evidence layers and exact results

### 6.1 Twenty real V12 calls

Role:

- real voice discovery;
- failure-taxonomy seed;
- scenario-design input;
- controlled PM demonstration of real agent behavior.

Limitations:

- recorded by Arnav in controlled scenarios;
- not representative customer traffic;
- labels are Codex-assisted and provisional;
- not causal evidence of candidate lift;
- not an estimate for SBI, LIC, or a production population.

The controlled baseline reported 15 matched calls plus five exploratory/stress calls. Among ten eligible matched calls, nine had an explicit pay-now commitment, which creates a ceiling problem for same-card voice TSR.

Primary paths:

- `voice-agent-improvement/improvement/baseline_selection.json`
- `voice-agent-improvement/improvement/human_annotations.json`
- `voice-agent-improvement/artifacts/baseline/`
- `voice-agent-improvement/artifacts/framework/emi/reference_annotations.provisional.jsonl`

### 6.2 Provisional evaluator calibration

Agreement against provisional references:

```text
primary_success                         1.00
hard_safety_violation                   1.00
integrity_violation                     0.85
task_success                            0.80
failure_category                        0.25
failure_owner                           0.25
first_breaking_turn within one turn     0.35
```

Interpretation:

- outcome and hard-safety labels are useful on this slice;
- component ownership and first-break localization are advisory;
- owner review is necessary before human-gold language;
- weak diagnostic agreement is shown rather than hidden.

### 6.3 Two-hundred-case failure-derived static library

Active version: `emi_failure_derived_v3`.

Composition:

- 120 development;
- 30 regression;
- 30 legacy held-out;
- 15 failure anchors;
- five preserved-win anchors;
- multilingual distribution across Hindi, Hinglish, English, and Punjabi.

Important correction:

- the former held-out shares source traces/generation machinery with development and was inspected;
- it is compromised as independent final evidence;
- it is retained for development diagnostics, challenge coverage, and regression debugging only;
- it must not be used to claim voice improvement.

Primary paths:

- `voice-agent-improvement/artifacts/framework/emi/datasets/emi_failure_derived_v3/manifest.json`
- `voice-agent-improvement/artifacts/framework/emi/datasets/emi_failure_derived_v3/integrity_audit.json`

### 6.4 Thirty stateful scenarios

Composition:

- 18 development;
- six validation;
- six regression.

Each scenario can encode:

- hidden caller goal;
- behavior decision tree;
- initial account state;
- expected final state;
- allowed and forbidden actions;
- required tools;
- terminal conditions;
- language/persona constraints;
- deterministic assertions.

Each trial receives fresh SQLite state to prevent cross-trial leakage.

Primary paths:

- `voice-agent-improvement/artifacts/framework/emi/dynamic_scenarios_v1/development.jsonl`
- `voice-agent-improvement/artifacts/framework/emi/dynamic_scenarios_v1/validation.jsonl`
- `voice-agent-improvement/artifacts/framework/emi/dynamic_scenarios_v1/regression.jsonl`
- `voice-agent-improvement/artifacts/framework/emi/dynamic_scenarios_v1/manifest.json`

### 6.5 Thirty-case stateful candidate comparison

Governing deterministic rescore:

| Candidate | Task successes | Experience | Result |
|---|---:|---:|---|
| V12 | 16/30 | 1.000 | Baseline |
| V13 | 23/30 | — | Rejected for trust/non-commitment regression |
| V14 | 29/30 | — | Rejected for a firm-today state regression |
| Native GEPA finalist | 28/30 | — | Rejected for one P1 state regression and one P0 guardrail regression |
| V15 | 30/30 after deterministic rescore | 0.905 | Eligible for fresh final |

The original V15 full-run summary recorded 29/30 before deterministic evaluator v3 rescoring. The immutable episode traces were not rerun; the versioned deterministic rescore records 30/30. Use `dynamic_release_v15.json` as the governing gate artifact and disclose the rescore lineage if asked.

V15 release artifact:

- 14 repaired task outcomes;
- zero task regressions;
- all baseline wins preserved;
- zero new severe regression under the governing evaluator;
- experience drop remained within the predeclared 0.10 floor;
- decision: `eligible_for_fresh_final_test`.

Primary paths:

- `voice-agent-improvement/artifacts/framework/emi/dynamic_experiments/v12-dynamic-full/`
- `voice-agent-improvement/artifacts/framework/emi/dynamic_experiments/v15-firm-today-full/`
- `voice-agent-improvement/artifacts/framework/emi/dynamic_release_v15.json`
- `voice-agent-improvement/artifacts/framework/emi/dynamic_release_gepa_finalist.json`
- `voice-agent-improvement/artifacts/framework/emi/selection.json`

### 6.6 Sealed group-separated text final

The final was authored and sealed only after method/candidate selection. It was opened once for V12 and once for V15. Do not regenerate or tune on it.

Result:

```text
V12:  5/12 = 41.7%
V15:  9/12 = 75.0%
repairs: 4
task regressions: 0
baseline experience: 1.0000
candidate experience: 0.9375
exact paired p: 0.125
decision: pass_text_final_awaiting_matched_voice
```

Secondary semantic diagnostics:

```text
faithfulness   3.833 → 4.000
conciseness    4.000 → 4.000
progression    3.833 → 3.750
```

No broad statistical-significance claim is permitted. Four discordant pairs in twelve cases are useful project evidence, not a population theorem.

Primary paths:

- `voice-agent-improvement/artifacts/framework/emi/dynamic_scenarios_v1/fresh_final_seal.json`
- `voice-agent-improvement/artifacts/framework/emi/fresh_final_decision.json`
- `voice-agent-improvement/artifacts/framework/emi/dynamic_experiments/v12-fresh-final/`
- `voice-agent-improvement/artifacts/framework/emi/dynamic_experiments/v15-fresh-final/`

### 6.7 Six-condition baseline acoustic diagnostic

The project ran six audio-condition diagnostics against V12. These were not adaptive EVA bot-to-bot conversations and were not a V12/V15 comparison.

Observed:

- pay-now intent recognized in 6/6;
- redundant confirmation appeared in 6/6;
- exact brand recognition was 0/6 with macOS synthetic TTS;
- legacy latency measurements that included caller streaming are not used as response latency.

Primary path:

- `voice-agent-improvement/artifacts/framework/emi/voice_stress_v1/live/voice_summary.json`

### 6.8 One valid realtime EVA–Samvaad run

Run ID:

```text
emi_eva_live_20260819_135630
```

Architecture:

```text
ElevenLabs realtime caller agent “Arnav”
            ⇅ live audio
project-owned EVA assistant-server adapter
            ⇅ Samvaad bidirectional WebSocket
deployed Sarvam Indus V12 agent “Shubh”
```

This was true audio-native bot-to-bot interaction. It was not a batch LLM → TTS loop and did not reconstruct Shubh using separate Saaras/LLM/Bulbul components.

Provider evidence:

```text
Sarvam connectivity                  connected
Sarvam end reason                    AGENT_ENDS
Sarvam failure reason                NO_FAILURE_REASON
Sarvam conversation duration         ~45.507 s
Sarvam average agent response        ~0.92 s
bridge mean response                 ~0.441 s
ElevenLabs recording duration        47 s
transport                            live bidirectional WebSocket audio
```

Evaluator used for this historical run: V7.

Scores:

```text
conversation valid end       1.0
user behavioral fidelity     1.0
user speech fidelity         1.0
task completion              1.0
faithfulness                 1.0
agent speech fidelity        1.0
turn taking                  0.5
conciseness                  1.0
conversation progression     0.5
EVA-A                        1.000
EVA-X                        0.667
overall                      0.833
```

First observed defect:

> After Arnav explicitly agreed to open the EasyCredit app and pay, Shubh asked for confirmation once more before closing.

This is an excellent demo defect because the task succeeded but the experience evaluator still caught unnecessary repetition.

Primary paths:

- `voice-agent-improvement/artifacts/eva_live/emi_eva_live_20260819_135630/`
- `voice-agent-improvement/artifacts/eva_live/emi_eva_live_20260819_135630/records/EMI-LIVE-001/`
- `dashboard/public/eva-live-run.json`

### 6.9 Frozen prospective 18-record voice suite

Current evaluator:

```text
evaluation-metrics.v3/loopline-eva-adapter.v1/samvaad-duplex.v10
```

Evaluator bundle SHA-256:

```text
35553ac8eac2fc60d275c41e434559534c5e3a7e03572c4bdfbb830df55b05d9
```

Suite:

- 12 core stateful scenarios;
- six deterministic acoustic-risk scenarios;
- background noise, low gain, packet loss, and jitter perturbations;
- identical record IDs and trial counts required for V12 and V15.

Current dataset SHA-256:

```text
99d6f0f37bba3595a6f3498b48f7dfee751d004af7980835725adb1612710f48
```

V10 differs from V9 only because the prospective caller identity was normalized from “Arnav Dhavala” to “Arnav.” Metrics, transport, state isolation, tool rules, and release gates did not change. Historical V7–V9 evidence remains immutable.

No baseline/candidate pair has been executed. The protocol exists; the result does not.

Primary paths:

- `voice-agent-improvement/artifacts/framework/emi/eva_adapter_v10/evaluator_freeze.json`
- `voice-agent-improvement/artifacts/framework/emi/eva_voice_suite_v1/manifest.json`
- `voice-agent-improvement/research/upstream/eva/data/emi_dataset.json`
- `voice-agent-improvement/research/upstream/eva/data/emi_scenarios/EMI-VOICE-*.json`

---

## 7. Evaluation Engine in detail

### 7.1 Evaluation layers

The evaluator uses separate layers rather than a single attractive score:

1. **Validity**
   - Did the caller follow its hidden goal?
   - Did the conversation finish?
   - Was caller speech faithful enough to score?
   - Was the provider/session failure infrastructure-owned?

2. **Deterministic execution truth**
   - Required actions.
   - Forbidden actions.
   - Dates, amounts, and entities.
   - Tool name, arguments, result, and order.
   - Initial/final state.
   - Say/do consistency.

3. **EVA-A / accuracy**
   - Task completion.
   - Faithfulness.
   - Agent speech fidelity.

4. **EVA-X / experience**
   - Turn taking.
   - Conciseness.
   - Conversation progression.

5. **Diagnostics**
   - Response speed.
   - STT WER when appropriate.
   - Speakability.
   - Key-entity transcription accuracy.
   - Language switch.
   - First breaking event.

### 7.2 Deterministic truth is primary

The release rules explicitly say:

```text
validation_before_scoring                true
deterministic_execution_truth_is_primary true
llm_judges_are_secondary                 true
missing_voice_evidence_is_not_a_pass     true
improvement_cannot_mutate_evaluator      true
```

This is a major design choice. Gemini may grade progression or concision, but it does not override an executable state/tool failure.

### 7.3 Simulator validation

Invalid simulator behavior must be excluded and regenerated rather than counted as an agent failure. Examples:

- caller reveals hidden facts too early;
- caller ignores the assigned goal;
- caller makes an impossible claim;
- caller fails to terminate under defined rules;
- provider failure prevents a substantive exchange.

### 7.4 First-breaking-event concept

The system localizes the first observable point after which the desired outcome became less likely or impossible. This is used for diagnosis, not as perfect ground truth.

Every failure packet should contain:

- run/scenario/version identifiers;
- evidence turn;
- expected behavior;
- observed behavior;
- severity;
- failure family;
- component owner;
- proposed repair surface;
- permanent test candidate.

Because current owner/localization agreement is weak, the UI must label first-break localization as provisional/advisory until owner review.

### 7.5 Evaluator version history

- Historical live run was scored under V7.
- V8/V9 added later protocol/tool/reliability changes.
- V10 is the frozen prospective evaluator.
- Do not relabel the V7 result as V10.
- A new evaluator version is required for any metric, threshold, scenario, transport, tool-state, or judge-contract change.

### 7.6 Gemini role

Gemini is used for text/semantic tasks where deterministic truth is insufficient. The live EVA wrapper currently configures:

- `gemini-3.1-pro-preview` as the primary text judge;
- `gemini-3-flash-preview` for the documented audio-fidelity path.

The project also used Gemini models in synthetic generation and candidate experiments. This creates same-family dependence and must be disclosed. Recommended future controls:

- owner review of all real references;
- independent second judge family;
- blind human audit of discordant cases;
- executable verifiers wherever possible;
- judge-disagreement reporting;
- no single LLM generating, proposing, and certifying every difficult case without checks.

---

## 8. Improvement Engine in detail

### 8.1 Failure routing before optimization

The repair registry covers:

| Failure owner | Repair route | Required gate |
|---|---|---|
| Prompt | Manual prompt or GEPA | Matched regression + fresh final + human diff |
| Extractor | Output-variable/extractor patch | Frozen transcript re-extraction |
| Tool | Tool schema/contract/implementation | Sandbox fixtures, auth, idempotency, state assertions |
| Workflow | State-machine/config change | Transition and scenario regression |
| Knowledge | Source/RAG update | Citation and freshness checks |
| Model/runtime | Model/runtime ablation | Matched model/config comparison |
| Voice/channel | STT/TTS/audio/runtime change | Matched acoustic/voice transfer |
| Policy | Human policy change | Named policy-owner approval |
| Evaluator | Judge/evaluator repair | Separate calibration/versioning experiment |

### 8.2 Manual repair arms

Manual prompt repairs were intentionally run independently of GEPA. This prevents a tool name from becoming the story and shows product judgment.

- V13 repaired stateful handling but caused trust/non-commitment regressions.
- V14 improved terminal discipline but left one firm-today state regression.
- V15 was selected after strict state/action rescoring.

Negative candidates remain in the experiment lineage.

### 8.3 GEPA Optimize Anything

What is true:

- a real local GEPA Optimize Anything search ran;
- it used full-episode failure feedback;
- candidate proposals, reflections, scores, and lineage were preserved;
- MLflow records the search;
- the stateful GEPA finalist reached 28/30.

What is also true:

- the finalist was rejected;
- it introduced one P1 state regression and one P0 guardrail regression;
- more optimizer calls are not automatically better evidence;
- another GEPA seed is intentionally deferred until live evaluation localizes a prompt-owned failure.

This rejection is valuable. It proves the release controller is independent of the optimizer.

### 8.4 Extractor arm

The output extractor was evaluated separately so a disposition-enum correction could not be misattributed to prompt improvement.

Primary path:

- `voice-agent-improvement/agent/candidates/extractor-v2/OUTPUT-VARIABLES.md`
- `voice-agent-improvement/artifacts/framework/emi/extractor/`

### 8.5 MLflow lineage

Tracking database:

```text
voice-agent-improvement/artifacts/experiments/mlflow.db
```

MLflow is the technical drill-down for:

- run IDs;
- prompt hashes;
- candidate IDs;
- metrics;
- failure cases;
- GEPA proposals/reflections;
- negative candidates;
- final artifacts.

Loopline is the PM/CXO operating UI. MLflow should not replace the product narrative.

### 8.6 What “self-improving” means operationally

The system is batch and human-gated:

```text
weekly traces → evaluate → diagnose → route → propose → compare → approve → canary → promote/hold/rollback
```

It is intentionally not recursive code self-modification, online RL, or autonomous production deployment. In regulated customer service, bounded, reviewable repair surfaces are defensible.

---

## 9. Release governance in detail

### 9.1 Release is independent from candidate generation

Neither GEPA nor a manual editor can promote a candidate. The release controller consumes frozen artifacts and emits a decision.

The release record must include:

- baseline ID and hash;
- candidate ID and hash;
- evaluator ID/hash;
- scenario/dataset hashes;
- trial counts and validity counts;
- per-case baseline/candidate outcomes;
- repairs and regressions;
- severity for each change;
- preserved-win status;
- experience delta;
- tool-state evidence where required;
- matched voice status;
- human approver;
- decision and rollback target;
- explicit claim boundary.

### 9.2 Hard-gate philosophy

Aggregate averages are insufficient. A candidate that fixes many easy cases but introduces one legal, fraud, safety, integrity, or terminal-state failure can be worse.

The current gate protects:

- zero new severe regressions;
- all baseline task wins preserved;
- experience drop no worse than the predeclared floor;
- exact paired evidence;
- separate fresh final;
- missing live evidence cannot count as pass.

### 9.3 Method freeze

The method freeze records prompt, evaluator, scenario, and selection hashes before the once-only final. The final test is not accessible to the optimizer.

Primary paths:

- `voice-agent-improvement/artifacts/framework/emi/method_freeze.json`
- `voice-agent-improvement/artifacts/framework/emi/selection.json`
- `voice-agent-improvement/artifacts/framework/emi/dynamic_scenarios_v1/fresh_final_seal.json`

### 9.4 Current decision state

Current decision:

```text
pass_text_final_awaiting_matched_voice
```

This is not production promotion. The next gate is human review plus matched Indus voice.

### 9.5 Why a negative live result is still interview-worthy

If V15 fails the voice gate, the project still demonstrates:

- evaluator catches transfer failures;
- text improvements do not automatically transfer to voice;
- release controller holds/rolls back rather than cherry-picking;
- exact first-break and component routing produce the next iteration backlog.

The product achievement is the decision system, not forcing a green score.

---

## 10. Realtime EVA ↔ Samvaad integration

### 10.1 Why EVA was chosen

ServiceNow EVA is the closest overall reference for this assignment because it separates:

- task/faithfulness/speech fidelity (Accuracy/EVA-A);
- progression/concision/turn-taking (Experience/EVA-X);
- simulator validity;
- realtime audio-native user simulation;
- preserved evaluation artifacts;
- repeated-run reliability concepts.

The project did not simply restyle a fake demo. It cloned and pinned EVA, retained its license, and added a project-owned Samvaad assistant-server implementation and EMI fixtures.

### 10.2 What runs on each side

Caller side:

- ElevenLabs Agents realtime agent;
- persona/name: Arnav;
- Indian male voice selected during provisioning;
- hidden EMI goal and low-attention persona;
- receives Shubh audio and responds with live audio;
- not the system under test.

Agent-under-test side:

- deployed Sarvam Indus / Samvaad agent;
- Shubh voice/persona;
- complete platform-managed voice agent;
- connected over Samvaad bidirectional WebSocket;
- not reconstructed locally using separate STT, LLM, and TTS.

Bridge:

- accepts EVA/Twilio-like media flow;
- streams caller audio to Samvaad;
- streams Shubh audio back to EVA;
- records events and timing;
- creates combined audio/transcript artifacts;
- supplies isolated scenario/tool context.

### 10.3 Key implementation files

- `voice-agent-improvement/research/upstream/eva/src/eva/assistant/samvaad_server.py`
- `voice-agent-improvement/scripts/run_eva_samvaad_live.py`
- `voice-agent-improvement/scripts/run_eva_samvaad_suite.py`
- `voice-agent-improvement/scripts/rescore_eva_samvaad_run.py`
- `voice-agent-improvement/scripts/recover_eva_samvaad_run.py`
- `voice-agent-improvement/scripts/compare_eva_samvaad_suites.py`
- `voice-agent-improvement/scripts/build_eva_emi_voice_suite.py`
- `voice-agent-improvement/scripts/provision_eva_elevenlabs_caller.py`

### 10.4 Live-run artifacts

Each valid run can preserve:

```text
audio_mixed.wav
audio_user.wav
audio_user_clean.wav
audio_assistant.wav
elevenlabs_audio_recording.mp3
transcript.jsonl
samvaad_events.jsonl
user_simulator_events.jsonl
framework_logs.jsonl
samvaad_transport.json
samvaad_runtime.json
initial_scenario_db.json
final_scenario_db.json
scenario_db.json
audit_log.json
result.json
metrics.json
elevenlabs_conversation_details.json
```

Infrastructure failures are preserved but excluded from agent-quality scoring. The valid run directory also contains earlier failed attempts; do not delete them.

### 10.5 Earlier overnight audio runs

An earlier implementation spent Sarvam credits on:

- three integration attempts that timed out without messages;
- one successful audio round-trip smoke test;
- six acoustic-condition runs;
- four latency-corrected reruns before an HTTP 402 response.

Those conversational runs repeated essentially the same scripted Riya/pay-now interaction. They were audio-in/audio-out tests but not adaptive EVA realtime user conversations. They must not be called full duplex bot-to-bot evaluation.

The later ElevenLabs Arnav ↔ Samvaad Shubh run is the genuine adaptive realtime bot-to-bot evidence.

### 10.6 Provider-session budget controls

The single-run wrapper intentionally allows:

- one record;
- one trial;
- one attempt;
- one ElevenLabs session;
- one Samvaad session;
- no automatic paid retries.

The suite wrapper requires:

- explicit `--max-sessions`;
- explicit live confirmation;
- identical trial count for baseline and candidate;
- dry-run mode for config validation;
- recorded invalid/provider-failure handling.

Do not remove these controls for convenience.

### 10.7 Stock EVA fallback

The plan originally asked for an untouched upstream EVA stock scenario. That requires EVA’s supported provider stack. The project instead preserves a disclosed adaptation.

Correct wording:

- “EVA-inspired evaluator with adapted components and a project-owned Samvaad adapter.”

Incorrect wording:

- “We ran untouched upstream EVA against Indus.”

The documented fallback is not a binding blocker as long as the claim remains accurate.

---

## 11. Execution-truth tool service

### 11.1 Purpose

Conversation text alone cannot prove that an agent executed a tool correctly. The project therefore implements a small scenario-isolated service that records tool name, arguments, result, order, and state mutation.

Implementation:

- `voice-agent-improvement/framework/tool_service.py`
- `voice-agent-improvement/scripts/run_tool_service.py`
- `voice-agent-improvement/INDUS-TOOL-CONNECTION.md`

### 11.2 State model

Every trial has its own:

- `run_id`;
- `account_id`;
- initial state;
- current state;
- append-only events;
- timestamps.

State includes:

```text
account_id
payment_status
outstanding_amount
promise_to_pay_date
callback
disposition
```

The store is SQLite. Unknown run IDs and account mismatches fail. Event IDs support idempotency.

### 11.3 Endpoints

Project-owned endpoints, not Sarvam endpoints:

```text
GET  /health
POST /v1/evaluation/runs
GET  /v1/evaluation/runs/{run_id}
POST /v1/tools/check-payment-status
POST /v1/tools/record-promise-to-pay
POST /v1/tools/schedule-callback
```

Tool behavior:

1. `check_payment_status`
   - reads payment status and outstanding amount;
   - does not invent completion.

2. `record_promise_to_pay`
   - requires `date` in `DD-MM-YYYY`;
   - writes promise date;
   - sets disposition `fptp`.

3. `schedule_callback`
   - requires date plus narrow time window;
   - writes callback state;
   - sets disposition `callback`.

### 11.4 Authentication

The service requires `LOOPLINE_TOOL_SECRET` and expects header:

```text
X-Loopline-Tool-Key
```

Seeding and state inspection always require the secret.

There is a default-off synthetic-evaluation bypass limited to the three tool-effect endpoints. It exists only for controlled evaluation environments because the Indus test runtime stripped the stored credential during a prior attempt. Production code must keep fail-closed authentication.

Never solve the integration issue by deploying a broadly unauthenticated public endpoint.

### 11.5 Current blocker

Code-side status:

- authenticated service implemented;
- isolated state implemented;
- idempotency implemented;
- three tools implemented;
- tests pass;
- EVA adapter integration path exists.

Evidence status:

- no live deployed Indus tool side effect has been captured;
- the Indus test runtime omitted the stored credential during the attempt;
- tool timeline in the dashboard is therefore unpopulated for real live evidence.

### 11.6 Required live proof

Before the matched suite:

1. Run the tool service locally.
2. Expose it through one approved authenticated HTTPS route.
3. Attach all three tools to the V15 draft.
4. Map `campaignId` to `run_id` and `transactionReference` to `account_id`.
5. Seed a fresh run.
6. Use Indus tool test.
7. Capture one HTTP 200 tool effect.
8. Read the run state.
9. Confirm tool, arguments, result, timestamps, and state diff.
10. Run one EVA smoke scenario that actually requires a tool.
11. Confirm transcript, tool event, scenario state, and spoken claim agree.

Only then can the project say that live execution truth is wired end-to-end.

---

## 12. Loopline product UI

### 12.1 Role

Loopline is the PM/CXO-facing product surface. It should answer:

> Which calls failed, exactly where, why, who owns the failure, what candidate changed, and why did the release gate promote, hold, or roll back it?

### 12.2 Current capabilities

- evaluation/improvement/release claims shown separately;
- high-level framework status;
- calls and traces;
- real EVA audio playback;
- scenario goal/persona;
- transcript timeline;
- first defect localization;
- initial/final scenario state;
- provider connection/timing evidence;
- EVA-A/EVA-X components;
- failure families and ownership;
- candidate and GEPA lineage;
- MLflow technical link/context;
- completion gates;
- claim boundary.

### 12.3 Current limitations

- live tool timeline has no real side-effect evidence yet;
- matched V12/V15 reliability panels have no paired live data yet;
- dashboard is local/static-export oriented, not production streaming observability;
- historical discovery labels remain provisional;
- no payment-ledger outcome join.

### 12.4 Important UI design choice

The ServiceNow EVA project page and demo inspired the information architecture, especially:

- user goal/persona on the left;
- conversation/audio in the center;
- tools on the right;
- visible criteria and failure details.

Loopline must use its own branding and implementation. Do not imply ServiceNow endorsement or present the static EVA website as our code.

### 12.5 Data files

- `dashboard/public/dashboard-data.json` — framework snapshot.
- `dashboard/public/eva-live-run.json` — redacted projection of the valid live run.
- `dashboard/app/page.tsx` — main UI.
- `dashboard/app/globals.css` — UI styling.
- `dashboard/tests/rendered-html.test.mjs` — render/information-architecture tests.

The dashboard projection intentionally displays the caller as “Arnav.” Historical raw files may retain “Arnav Dhavala” to preserve evidence integrity.

### 12.6 Current verification

Latest verification records:

- 79 Python tests passed;
- dashboard lint passed;
- dashboard rendered-page tests passed;
- dashboard production build passed;
- frozen hashes passed;
- final protocol checks passed;
- credential-pattern scan passed.

The generated completion-audit note still says “78 Python tests” in one field; this is stale wording. The actual verifier command output says `Ran 79 tests` and is authoritative.

### 12.7 UI commands

```bash
cd /Users/Arnav/Claude/Projects/Sarvam/dashboard
npm run dev
```

Open:

```text
http://localhost:3000
```

Production verification:

```bash
npm run lint
npm test
npm run build
```

---

## 13. MLflow

### 13.1 Purpose

MLflow is used for technical experiment lineage, not as the primary product UI.

Tracking backend:

```text
/Users/Arnav/Claude/Projects/Sarvam/voice-agent-improvement/artifacts/experiments/mlflow.db
```

### 13.2 Start the UI

```bash
cd /Users/Arnav/Claude/Projects/Sarvam/voice-agent-improvement
source .venv/bin/activate
mlflow ui \
  --backend-store-uri sqlite:///artifacts/experiments/mlflow.db \
  --port 5000
```

Open:

```text
http://127.0.0.1:5000
```

Starlette WSGI deprecation warnings are not an experiment failure. Multiple Uvicorn worker messages are normal for the local UI.

### 13.3 What has been logged

- baseline and candidate runs;
- manual candidate experiments;
- GEPA search lineage;
- GEPA proposals/reflections/Pareto artifacts;
- stateful episode summaries;
- prompt hashes;
- final artifacts;
- negative candidates.

### 13.4 Best-practice position

The current implementation is sufficient for an interview MVP. A production version could add:

- MLflow Prompt Registry;
- MLflow evaluation datasets;
- native row-level GenAI traces;
- parent/child optimizer runs;
- token/cost logging;
- environment lock and source commit;
- model-resolution metadata;
- registered release artifacts.

Do not rerun experiments solely to make the tracking UI prettier.

---

## 14. Repository map

### 14.1 Top level

```text
/Users/Arnav/Claude/Projects/Sarvam/
├── BUILD-PLAN.html
├── CALL-RECORDING-GUIDE.html
├── EXECUTION-AUDIT.html
├── FINAL-EXECUTION-REPORT.html
├── FINAL-INTERVIEW-DECISION.html
├── FINAL-PLAN.html
├── PRESENTATION-READY-COMPLETION-PLAN.html
├── SELF-IMPROVING-AGENT-FRAMEWORK.html
├── Project_Plan_and_Architecture.md
├── handoff.md
├── dashboard/
└── voice-agent-improvement/
```

### 14.2 Core framework package

`voice-agent-improvement/framework/`

Core and IO:

- `core/schemas.py` — canonical structures and hashes.
- `core/io.py` — artifact IO helpers.
- `domain.py` — domain-pack structures.
- `domain_packs/emi.json` — active reference domain.
- `domain_packs/hospital_appointments.json` — portability schema smoke.

Ingestion and datasets:

- `ingestion/canonicalize.py` — real-call canonicalization.
- `datasets/derive_emi.py` — failure-derived cases.
- `datasets/migrate_outcomes_v3.py` — exact Indus outcome migration.
- `datasets/repair_v3_anchors.py` — anchor contract repair.
- `datasets/audit_integrity.py` — split/source leakage audit.
- `datasets/domain_smoke.py` — second-domain smoke.

Evaluation:

- `evaluation/contracts.py` — stateful scenario contracts.
- `evaluation/environment.py` — isolated execution environment.
- `evaluation/metrics.py` — deterministic task/experience metrics.
- `evaluation/semantic_metrics.py` — semantic secondary scoring.
- `evaluation/voice_metrics.py` — voice diagnostics.
- `evaluation/adaptive_caller.py` — adaptive caller support/cache.
- `evaluation/live_budget.py` — provider-session limits.
- `evaluation/live_release.py` — exact live paired gate.
- `evaluation/release.py` — dynamic gate.
- `evaluation/runner.py` — scenario runner.
- `evaluation/run_dynamic.py` — dynamic suite runner.
- `evaluation/run_dynamic_gepa.py` — stateful GEPA runner.
- `evaluation/rescore.py` — versioned deterministic rescore.
- `evaluation/candidates.py` — candidate loading/hash.
- `evaluation/build_emi_scenarios.py` — 30-scenario builder.
- `evaluation/build_fresh_final.py` — group-separated final builder.
- `evaluation/build_voice_stress.py` — acoustic-risk fixtures.
- `evaluation/freeze_method.py` — method freeze.
- `evaluation/freeze_evaluator.py` — evaluator freeze.
- `evaluation/final_decision.py` — sealed-final decision.
- `evaluation/select_candidate.py` — independent candidate selection.
- `evaluation/adapters/indus.py` — Indus audio adapter/components.
- `evaluation/adapters/sarvam_speech.py` — standard Sarvam speech adapter; not the Samvaad duplex path.

Legacy/static evaluator layer retained for lineage:

- `evaluators/deterministic.py`
- `evaluators/semantic.py`
- `evaluators/calibrate.py`

Diagnosis and repairs:

- `diagnosis/router.py` — first-break/component owner routing.
- `repairs/registry.py` — allowed repair surfaces.

Experiments:

- `experiments/run_offline.py`
- `experiments/run_gepa.py`
- `experiments/evaluate_extractor.py`
- `experiments/tracking.py`

Operations/governance:

- `release/gate.py`
- `tool_service.py`
- `completion_audit.py`
- `report.py`
- `export_dashboard.py`
- `verify.py`
- `pipeline.py`

### 14.3 Sarvam Voice Agents API package

`voice-agent-improvement/sarvam_voice_agents/`

- `config.py` — environment-backed configuration.
- `client.py` — documented API request handling.
- `cli.py` — dry-run/explicit outbound call CLI and safe redaction.
- `analytics.py` — documented attempts/transcripts retrieval.

The Instant Outbound endpoint used is:

```text
POST https://apps.sarvam.ai/api/outbounds/v1/orgs/{org_id}/workspaces/{workspace_id}/outbounds
```

Do not invent undocumented endpoints.

### 14.4 Scripts

`voice-agent-improvement/scripts/`

- `build_eva_emi_voice_suite.py` — generates prospective EVA records/scenarios.
- `provision_eva_elevenlabs_caller.py` — provisions/reuses the ElevenLabs caller.
- `run_eva_samvaad_live.py` — one guarded live conversation.
- `run_eva_samvaad_suite.py` — guarded matched suite.
- `compare_eva_samvaad_suites.py` — exact paired live decision.
- `rescore_eva_samvaad_run.py` — score preserved live artifacts.
- `recover_eva_samvaad_run.py` — recover interrupted live output.
- `export_submission_evidence.py` — redacted UI projection.
- `run_tool_service.py` — tool service launcher.

### 14.5 Prompt/candidate artifacts

- `agent/v1/SYSTEM-PROMPT.md` — frozen seed/baseline prompt used by framework; path name is historical and can confuse.
- `agent/v1/INITIAL-MESSAGE.txt` — frozen greeting.
- `agent/v1/OUTPUT-VARIABLES.md` — baseline output contract.
- `agent/candidates/v13-stateful.md` — rejected manual arm.
- `agent/candidates/v14-terminal-discipline.md` — rejected manual arm.
- `agent/candidates/v15-firm-today.md` — selected candidate.
- `agent/candidates/gepa-v3-deployable/SYSTEM-PROMPT.md` — earlier static GEPA-derived candidate retained for lineage.
- `agent/candidates/extractor-v2/OUTPUT-VARIABLES.md` — extractor repair.

### 14.6 Tests

The test suite covers:

- API client/config/CLI and redaction;
- dataset contracts and integrity;
- canonicalization;
- diagnosis and repair routing;
- deterministic/semantic evaluation;
- Gemini adapter/cache boundaries;
- dynamic stateful scenarios;
- candidate selection and release gates;
- fresh final protocol;
- evaluator freezes;
- live budgets and live release;
- adaptive caller behavior;
- Sarvam speech adapter;
- tool-service auth, isolation, and idempotency;
- completion-audit integrity.

Latest verifier output: `Ran 79 tests ... OK`.

### 14.7 Research clones

`voice-agent-improvement/research/upstream/`

- `eva/` — pinned ServiceNow EVA clone with disclosed project adaptations.
- `tau2-bench/` or equivalent τ checkout — pinned reference.
- `riley-agent/` — pinned provider/tool reference linked from VAmoS.

Do not delete licenses or upstream metadata.

---

## 15. Planning and presentation artifact catalog

### 15.1 `FINAL-INTERVIEW-DECISION.html` — current primary plan

Title: **Final decision — Self-improving voice-agent framework**

Status: current presentation and completion plan.

Key sections:

- two engines, one closed loop;
- machine-verified acceptance;
- what is true today;
- research decision;
- target architecture;
- Gate Zero;
- P0–P6 roadmap;
- predeclared improvement routes;
- Loopline product narrative;
- interview claims;
- definition of done.

Use this for the final narrative. Its acceptance section says the local build is complete and four binding gates remain.

### 15.2 `FINAL-EXECUTION-REPORT.html`

Title: **Loopline — Final execution report**

Status: strong text-loop report and interview narrative, but it predates the final matched live completion gates.

Useful sections:

- text loop complete;
- frozen candidate and sealed comparison;
- evaluation/improvement separation;
- rejected high scores;
- component evidence versus fake voice win;
- defendable claims;
- demo story.

### 15.3 `PRESENTATION-READY-COMPLETION-PLAN.html`

Title: **Self-Improving Voice Agent · Completion Plan**

Status: research-driven bridge from the earlier prompt experiment to the final framework.

Key contribution:

- EVA as closest overall reference;
- VAmoS execution truth fills EVA’s main gap;
- three kinds of truth;
- accuracy/experience/reliability separation;
- seven-phase completion program;
- strict release gate as product.

### 15.4 `SELF-IMPROVING-AGENT-FRAMEWORK.html`

Title: **Self-Improving Agent Framework — Audited Plan**

Status: strongest case-agnostic conceptual design before final execution.

Key contribution:

- domain pack as portability boundary;
- route before optimizing;
- multiple replaceable repair layers;
- framework remains useful even if no candidate wins;
- EMI as proof fixture rather than the product itself.

### 15.5 `EXECUTION-AUDIT.html`

Title: **Self-Improving Voice Agent — Execution Audit**

Status: historical audit created when GEPA was overemphasized and other framework components needed clarification.

Useful for understanding:

- failure-derived dataset;
- what was actually executed;
- Optimize Anything status;
- what remained from the old final plan.

Current completion status is newer and lives in `completion_audit.json` and `FINAL-INTERVIEW-DECISION.html`.

### 15.6 `FINAL-PLAN.html`

Title: **Voice Agent Quality Flywheel — Implementation Plan**

Status: earlier detailed full plan with flowcharts.

Useful principles retained:

- reset evidence but keep working agent;
- measure verbal objective honestly;
- generate tests from observed failures;
- use multiple evaluators;
- find first failure;
- GEPA as one repair engine;
- text as gate, voice as proof;
- scale-to-millions framing.

Some counts and implementation details are superseded.

### 15.7 `CALL-RECORDING-GUIDE.html`

Title: **Call Recording Guide — Voice Agent Quality Flywheel**

Status: historical human recording guide for the V12 baseline and matched cards.

Useful principles:

- controlled caller behavior;
- preserve failures;
- unique run IDs;
- language and objection scenarios;
- do not improvise account facts;
- repeat cards, not remembered conversations.

The final prospective suite is automated EVA realtime, so this is no longer the sole execution protocol.

### 15.8 `BUILD-PLAN.html`

Title: **Build Plan — Self-Improving Voice Agents · 14 Days**

Status: early planning artifact.

Useful for historical intent only. It includes a 14-day schedule and older stack assumptions.

### 15.9 `Project_Plan_and_Architecture.md`

Status: earliest broad architecture. It mentions a cascaded STT/LLM/TTS simulation and four-week plan. This is superseded for live agent evaluation because the final architecture evaluates the complete Samvaad agent through its bidirectional audio WebSocket.

Do not present Saaras + local LLM + Bulbul as the current EVA agent-under-test path.

### 15.10 `voice-agent-improvement/PROJECT-PHASES.md`

Status: stale historical phase document. It still discusses the 150-case library, “human gold,” and V13 as next. Do not use it as current truth.

### 15.11 `handoff.md`

This file is now the single consolidated Claude Code handoff and current context index.

---

## 16. Environment and dependencies

### 16.1 Python project

Package:

```text
sarvam-voice-agent-improvement 0.2.0
Python >= 3.11
```

Primary dependencies:

```text
requests
certifi
pydantic
fastapi
uvicorn
sarvam-conv-ai-sdk 1.0.21
sarvamai 0.1.30
```

Experiment extras:

```text
gepa >=0.1.4,<0.2
mlflow >=3.1,<4
```

There are two Python environments of interest:

- `voice-agent-improvement/.venv` for the project framework;
- `voice-agent-improvement/research/upstream/eva/.venv` for the pinned EVA runtime.

### 16.2 Dashboard project

Key stack:

- React 19;
- TypeScript 5.9;
- Vite 8;
- vinext beta;
- Tailwind/PostCSS;
- Node >= 22.13.

### 16.3 Environment-variable names

Do not include values in logs or documentation.

Voice Agents:

```text
SARVAM_VOICE_AGENTS_API_KEY
SARVAM_ORG_ID
SARVAM_WORKSPACE_ID
SARVAM_APP_ID
SARVAM_APP_VERSION
SARVAM_CONNECTION_ID
SARVAM_AGENT_PHONE_NUMBER
SARVAM_TEST_USER_PHONE_NUMBER
```

Standard Sarvam speech API, only for separate speech-component experiments:

```text
SARVAM_API_KEY
```

Gemini:

```text
GEMINI_API_KEY
```

ElevenLabs/EVA:

```text
ELEVENLABS_API_KEY
EVA_EN_USER_M
```

Tool service:

```text
LOOPLINE_TOOL_SECRET
LOOPLINE_TOOL_BASE_URL
LOOPLINE_TOOL_DB
```

Voice Agents API keys and standard Sarvam STT/TTS keys are separate. Do not interchange them.

---

## 17. Operational commands

### 17.1 Verify the whole local project

```bash
cd /Users/Arnav/Claude/Projects/Sarvam/voice-agent-improvement
source .venv/bin/activate
python -m framework.verify
```

This runs:

- Python unit tests;
- dashboard lint;
- dashboard tests;
- dashboard production build;
- evaluator freeze/hash checks;
- fresh-final protocol checks;
- credential-pattern scan.

Latest known result:

```text
passed: true
verified_at: 2026-08-19T17:42:30.352344+00:00
Python: 79 tests, all passed
dashboard lint: passed
dashboard tests: passed
dashboard build: passed
```

Warnings about missing PyAudio or Starlette deprecation are currently non-fatal. The realtime EVA path does not depend on local PyAudio playback.

### 17.2 Refresh plan-level completion status

```bash
cd /Users/Arnav/Claude/Projects/Sarvam/voice-agent-improvement
source .venv/bin/activate
python -m framework.completion_audit
```

Output:

```text
artifacts/framework/completion_audit.json
```

This audit must keep external gates open. Do not convert “harness exists” into “live evidence passed.”

### 17.3 Refresh execution report and dashboard data

```bash
cd /Users/Arnav/Claude/Projects/Sarvam/voice-agent-improvement
source .venv/bin/activate
python -m framework.report
python -m framework.export_dashboard
python scripts/export_submission_evidence.py
```

After changing frozen suite components, create a new evaluator version before refreshing derived data.

### 17.4 Framework pipeline status

```bash
cd /Users/Arnav/Claude/Projects/Sarvam/voice-agent-improvement
source .venv/bin/activate
python -m framework.pipeline status
python -m framework.pipeline report
python -m framework.pipeline export-dashboard
```

### 17.5 Start Loopline

```bash
cd /Users/Arnav/Claude/Projects/Sarvam/dashboard
npm run dev
```

Open `http://localhost:3000`.

### 17.6 Start MLflow

```bash
cd /Users/Arnav/Claude/Projects/Sarvam/voice-agent-improvement
source .venv/bin/activate
mlflow ui \
  --backend-store-uri sqlite:///artifacts/experiments/mlflow.db \
  --port 5000
```

Open `http://127.0.0.1:5000`.

### 17.7 Safe Instant Outbound dry run

```bash
cd /Users/Arnav/Claude/Projects/Sarvam/voice-agent-improvement
source .venv/bin/activate
python -m sarvam_voice_agents.cli \
  --variables examples/emi-reminder.variables.json
```

Expected behavior: redacted payload, no call.

### 17.8 Real Instant Outbound call

Do not run without explicit current authorization.

```bash
python -m sarvam_voice_agents.cli \
  --variables examples/emi-reminder.variables.json \
  --execute \
  --confirm-call
```

### 17.9 Start the local tool service

Requires `LOOPLINE_TOOL_SECRET` in `.env`.

```bash
cd /Users/Arnav/Claude/Projects/Sarvam/voice-agent-improvement
source .venv/bin/activate
python scripts/run_tool_service.py --host 127.0.0.1 --port 8788
```

Local base URL:

```text
http://127.0.0.1:8788
```

Indus must use a secure public HTTPS route, not localhost.

### 17.10 Single EVA live dry run

Use the EVA virtual environment:

```bash
cd /Users/Arnav/Claude/Projects/Sarvam/voice-agent-improvement
source research/upstream/eva/.venv/bin/activate
python scripts/run_eva_samvaad_live.py --dry-run
```

No provider sessions should be spent.

### 17.11 Single EVA live conversation

Do not run without explicit current authorization.

```bash
cd /Users/Arnav/Claude/Projects/Sarvam/voice-agent-improvement
source research/upstream/eva/.venv/bin/activate
python scripts/run_eva_samvaad_live.py --confirm-live
```

The wrapper allows only one record/trial/attempt.

### 17.12 Prospective suite dry run

```bash
cd /Users/Arnav/Claude/Projects/Sarvam/voice-agent-improvement
source research/upstream/eva/.venv/bin/activate
python scripts/run_eva_samvaad_suite.py \
  --app-version 12 \
  --suite core \
  --trials 1 \
  --max-sessions 12 \
  --dry-run
```

### 17.13 Three-call pilot

Before the full matched suite, run three representative realtime records. Do not change the frozen records or evaluator based on whether V15 looks good. Changes after a pilot require a new candidate/evaluator version and a new predeclared protocol.

The exact CLI options for record selection should be read from:

```bash
python scripts/run_eva_samvaad_suite.py --help
```

Choose one straightforward pay-now case, one state/tool-dependent case, and one language/experience risk case. Use the same cases and trial counts for V12 and V15 if making any comparison.

### 17.14 Full frozen matched suite

After live tool smoke, exact V15 commit, and pilot approval:

```bash
cd /Users/Arnav/Claude/Projects/Sarvam/voice-agent-improvement
source research/upstream/eva/.venv/bin/activate

python scripts/run_eva_samvaad_suite.py \
  --app-version 12 \
  --suite all \
  --trials 1 \
  --max-sessions 18 \
  --confirm-live-suite

python scripts/run_eva_samvaad_suite.py \
  --app-version 15 \
  --suite all \
  --trials 1 \
  --max-sessions 18 \
  --confirm-live-suite
```

The version number `15` is valid only after the exact V15 candidate is actually committed under that immutable Indus app version. If Indus assigns another version, use the real version and record the mapping.

### 17.15 Compare matched live suites

```bash
cd /Users/Arnav/Claude/Projects/Sarvam/voice-agent-improvement
source .venv/bin/activate
python scripts/compare_eva_samvaad_suites.py \
  --baseline artifacts/eva_matched_live/<v12-run-id> \
  --candidate artifacts/eva_matched_live/<v15-run-id>
```

The resulting decision must be preserved even if it is hold or rollback.

### 17.16 Re-freeze evaluator only after a legitimate version change

Current V10 freeze already exists. Do not rerun unnecessarily.

If and only if a real evaluator/suite change is approved:

```bash
cd /Users/Arnav/Claude/Projects/Sarvam/voice-agent-improvement
source .venv/bin/activate
python -m framework.evaluation.freeze_evaluator --version <new-version>
```

Update every current pointer, tests, docs, and claim boundary. Historical results remain on their old evaluator versions.

---

## 18. Exact remaining work, in execution order

### Gate 1 — Owner truth and security confirmation

Owner: Arnav.

Tasks:

1. Review all 20 provisional reference annotations.
2. For each call confirm:
   - eligibility;
   - primary success;
   - task success;
   - disposition;
   - integrity/safety flags;
   - first observable breaking turn;
   - failure family;
   - component owner.
3. Version the reviewed labels rather than overwriting provisional artifacts.
4. Re-run evaluator calibration against owner truth.
5. Confirm the Voice Agents API key pasted earlier was rotated.

Exit artifact:

- versioned owner-reviewed references covering all 20 run IDs;
- new calibration summary;
- account-level key-rotation confirmation without exposing the key.

### Gate 2 — Live execution truth

Owner: framework + Arnav’s Indus account actions.

Tasks:

1. Start run-isolated tool service.
2. Expose secure public HTTPS route.
3. Confirm the route is accessible from Sarvam’s tool caller.
4. Configure secure `X-Loopline-Tool-Key` authentication in Indus.
5. Attach all three tools to the V15 draft.
6. Map run/account variables correctly.
7. Seed one test run.
8. Execute one tool through Indus.
9. Verify append-only event and before/after state.
10. Run one live EVA scenario requiring the tool.
11. Confirm transcript, tool event, and state agree.

Exit artifact:

- one Samvaad trace with tool name, arguments, result, timestamps, and before/after state.

Hard rule:

- do not expose a public unauthenticated endpoint as a shortcut.

### Gate 3 — Exact immutable V15 commit

Owner: Arnav.

Tasks:

1. Open `agent/candidates/v15-firm-today.md`.
2. Verify SHA-256 equals the frozen candidate hash.
3. Paste the exact prompt into an Indus draft.
4. Confirm Shubh voice.
5. Confirm short greeting.
6. Confirm EasyCredit and Samsung TV wording.
7. Confirm no unwanted customer-verification flow.
8. Confirm all required input variables exist.
9. Confirm output enum and extractor.
10. Confirm three tool descriptions and mappings.
11. Resolve real Genie contradictions, but do not allow Genie to rewrite policy.
12. Review exact prompt/config diff.
13. Commit one immutable app version.
14. Record Indus app version, prompt hash, extractor version, tool config hash, and rollback version.

Exit artifact:

- exact immutable deployed candidate mapping.

### Gate 4 — Pilot and matched live voice

Owner: framework, after explicit live-call authorization.

Tasks:

1. Run three representative pilot scenarios.
2. Inspect:
   - caller validity;
   - audio quality;
   - termination;
   - transcript;
   - tool state;
   - response timing;
   - overlap/interruptions;
   - identity/language behavior.
3. If infrastructure fails, fix infrastructure and rerun invalid sessions.
4. If agent behavior fails, preserve the failure; do not rewrite history.
5. After pilot approval, run all 18 frozen records on V12.
6. Run the same 18 records on V15.
7. Keep trials, state, simulator, acoustic perturbations, and scoring identical.
8. Blind-score/compare exact paired outcomes.
9. Apply hard per-case gate.
10. Emit signed promote, hold, or rollback.
11. Refresh Loopline with tool and reliability evidence.

Exit artifact:

- matched baseline/candidate directories;
- exact per-case decision;
- audio links;
- tool state;
- signed release record;
- bounded claim.

### Optional later gate — business outcome join

Required only before claiming cash lift or production business impact.

Add:

- payment ledger or CRM join;
- call/account privacy controls;
- attribution window;
- duplicate/retry logic;
- cohort definitions;
- canary/control assignment;
- settlement success;
- complaints/escalations/repeat-contact outcomes.

---

## 19. Security, privacy, and cost boundaries

### 19.1 Credential state

The conversation history previously contained a Voice Agents API key. Treat it as exposed. Rotation is a binding owner action.

Never add the raw key to:

- markdown;
- HTML;
- dashboard JSON;
- screenshots;
- MLflow artifacts;
- logs;
- Git;
- tool definitions exported for presentation.

### 19.2 Secret-scan boundary

`framework.verify` runs a credential-pattern scan. A passing scan is helpful but does not prove a key was rotated or that every external artifact is safe.

### 19.3 PII

The active EMI identities and account data are fictional. Phone numbers and platform identifiers still require care.

Before public sharing:

- remove or redact phone numbers;
- remove signed recording URLs;
- remove credentials and connection secrets;
- retain only fictional customer/account data;
- avoid exposing provider conversation IDs unless needed;
- state that EasyCredit data is fictional.

### 19.4 Paid providers

Paid resources can include:

- Sarvam Samvaad sessions/credits;
- ElevenLabs realtime agent sessions;
- Gemini API calls;
- standard Sarvam speech API calls if used.

The project added explicit session budgets because a prior overnight run consumed about 63 Sarvam credits on integration/acoustic tests without producing the intended adaptive bot-to-bot evidence.

Cost discipline:

- dry run first;
- one-record live smoke;
- three pilots;
- full suite only after the blocker is cleared;
- no automatic paid retries;
- no additional GEPA runs merely for volume.

### 19.5 Destructive changes

Do not delete:

- failed provider attempts;
- rejected candidates;
- historical evaluator versions;
- old raw artifacts with the prior caller name;
- fresh-final access logs;
- hashes or license notices.

Version new artifacts instead.

---

## 20. Research provenance and design borrowing

### 20.1 ServiceNow EVA

Repository:

```text
https://github.com/ServiceNow/eva
```

Paper:

```text
https://arxiv.org/abs/2605.13841
```

Datasets:

```text
https://huggingface.co/datasets/ServiceNow-AI/eva-bench
https://huggingface.co/datasets/ServiceNow-AI/eva
```

Pinned commit:

```text
e0041e3d9d4e706b21630a3ecb7595855004d63f
```

License: MIT.

Used for:

- realtime user-simulator runtime;
- assistant-server contract;
- Accuracy × Experience separation;
- simulator validation;
- evaluation artifact structure;
- reliability concepts.

Project additions:

- Samvaad server adapter;
- EMI fixtures;
- Indus-specific config;
- Gemini judge routing;
- isolated tool-state integration;
- Loopline export/UI.

Keep upstream MIT notice and do not imply ServiceNow endorsement.

### 20.2 τ / τ-Voice

Repository:

```text
https://github.com/sierra-research/tau2-bench
```

Paper:

```text
https://arxiv.org/abs/2603.13686
```

Pinned commit:

```text
a2c024725189473d2d7cea3a5cfdbcc67478e41f
```

License: MIT.

Used as design reference for:

- hidden user goals;
- state-equivalent task success;
- action/tool assertions;
- user simulation;
- matched perturbations;
- latency semantics;
- reliability measures.

The project does not claim to run the official τ-Voice benchmark.

### 20.3 VAmoS and Riley

Paper:

```text
https://arxiv.org/abs/2607.27453
```

Public agent repo:

```text
https://github.com/veris-ai/riley-agent
```

Pinned Riley commit:

```text
a22e0e96e68778c16761e05ebd2d3931d713f525
```

The complete VAmoS benchmark/simulation platform is not public. Do not claim a VAmoS fork or integration.

Used as design inspiration for:

- isolated backend state;
- joint transcript/tool truth;
- tool name/argument/result/order assertions;
- say/do mismatch detection;
- financial-services evaluation framing.

The Loopline tool/state grader is independently implemented and should be called “VAmoS-inspired.”

### 20.4 GEPA Optimize Anything

Primary sources:

```text
https://gepa-ai.github.io/gepa/
https://gepa-ai.github.io/gepa/blog/2026/02/18/introducing-optimize-anything/
https://gepa-ai.github.io/gepa/api/optimize_anything/optimize_anything/
```

Used as a real prompt-repair engine. The local library API ran; this was not a hosted “Optimize Anything API.”

GEPA does not define truth or approve release.

### 20.5 MatrAIx

Sources:

```text
https://matraix.ai/
https://arxiv.org/html/2608.04205v1
```

Used only as conceptual inspiration for:

- persona variation;
- cohort/behavior attributes;
- simulator validity;
- population-style thinking.

The project does not run MatrAIx or use its dataset.

### 20.6 Harbor

Source:

```text
https://www.harborframework.com/
```

Considered for sandboxed task/evaluation structure. Not integrated because the project now owns a smaller purpose-built state/tool environment and a large Harbor dependency would not improve the interview proof.

### 20.7 Licensing files

- `voice-agent-improvement/UPSTREAM_SOURCES.md`
- `voice-agent-improvement/THIRD_PARTY_NOTICES.md`

Rules:

- preserve upstream licenses;
- record pinned commit;
- document adapted files;
- audit third-party assets/dependencies separately;
- use project branding;
- do not imply endorsement.

---

## 21. Historical project timeline and why decisions changed

### 21.1 Initial idea

The first idea was to use GEPA because it was technically deep, interview-relevant, and associated with serious enterprise AI work. Early planning risked making the project look like:

```text
generate transcripts → optimize prompt with GEPA → generate transcripts again → show higher TSR
```

That was rejected as insufficiently defensible.

### 21.2 Platform choice

The project initially discussed a cascaded voice stack using STT, LLM, and TTS products. Once Sarvam Indus Voice Agents became available, the direction shifted to evaluating the managed complete agent because that is the product under test.

Key correction:

- Sarvam-30B is an LLM, not the single voice system.
- For the final live evaluator, use Samvaad’s bidirectional audio WebSocket.
- Do not reconstruct Shubh with separate Saaras + LLM + Bulbul.

### 21.3 Working agent and call collection

The EMI example became the concrete validation case. The user recorded controlled calls and observed:

- long opening caused disengagement;
- full TV specifications were unnecessary;
- “4K” pronunciation was bad;
- directness mattered;
- repetition after commitment was a recurring failure;
- English/Punjabi switching needed explicit coverage.

V12 became the practical baseline. Twenty calls were frozen as discovery evidence.

### 21.4 Dataset and evaluation correction

An initial synthetic library was generated. Later audits found:

- some generated rows were under-specified;
- generic outcome vocabulary did not match Indus;
- source-trace overlap compromised held-out independence;
- static next-turn cases were not voice proof.

Rather than hiding these issues, V1/V2 were invalidated, V3 was repaired, and the entire 200-row library was demoted to development diagnostics.

### 21.5 Framework expansion

The architecture evolved from prompt optimization to:

- ingestion and canonical traces;
- failure clustering;
- first-break localization;
- repair routing;
- static and stateful tests;
- manual/GEPA/extractor arms;
- MLflow lineage;
- strict release gates;
- fresh final;
- Loopline UI.

### 21.6 Research reset

Recent papers triggered an unbiased audit:

- EVA highlighted dynamic realtime bot-to-bot evaluation and Accuracy × Experience.
- τ-Voice highlighted full-duplex audio, perturbations, and reliability.
- VAmoS highlighted execution truth and isolated tool/backend state.

The project preserved prior work as the improvement/control plane and added the missing evaluation/runtime layer instead of discarding everything.

### 21.7 Overnight execution issue

An overnight run consumed credits on audio tests that were later recognized as scripted audio round trips, not adaptive two-agent full-duplex evaluation. This was explicitly corrected.

### 21.8 Genuine realtime integration

ElevenLabs was added as the realtime caller because EVA officially supports it. A project-owned adapter connected that live caller to the complete Samvaad agent. One valid run was captured and scored.

### 21.9 Current end state

The local framework is implemented through the prospective live gate. The remaining tasks are evidence collection and external/account configuration, not another architectural reset.

---

## 22. Known inconsistencies and stale artifacts

### 22.1 Test-count wording

- Latest verifier output: 79 Python tests.
- One generated completion-audit note says 78.
- Use 79 because the verifier command output is authoritative.
- Fix the audit wording on the next legitimate artifact refresh, without changing gate status.

### 22.2 V15 29/30 versus 30/30

- Original full-run aggregate: 29/30.
- Versioned deterministic evaluator v3 rescore of immutable traces: 30/30.
- Governing paired release artifact: 30/30.
- The agent/simulator was not rerun for the rescore.
- Disclose this evaluator-version lineage if a reviewer asks.

### 22.3 V7 live score versus V10 prospective evaluator

- The valid live run was scored under V7.
- V10 is frozen for future matched runs.
- Never claim the historical call was run under V10.

### 22.4 Caller name

- Active prospective identity: Arnav.
- Dashboard projection: Arnav.
- Suite/scenario generator: Arnav.
- Some historical raw artifacts: Arnav Dhavala.
- Do not rewrite historical raw evidence; explain that V10 normalizes the future caller identity.

### 22.5 Old planning files

- `PROJECT-PHASES.md` is stale.
- `Project_Plan_and_Architecture.md` uses older cascaded architecture.
- old HTMLs contain superseded counts and timelines.
- `FINAL-INTERVIEW-DECISION.html` plus machine artifacts are current.

### 22.6 Stock EVA claim

An untouched stock EVA run was not completed because the full supported provider stack was not configured. The adaptation is disclosed and licensed. Do not misrepresent it.

### 22.7 Tool configuration

The tool service is complete and tested, but no live Indus side effect exists. UI panels should show an empty/pending state, not synthetic live success.

### 22.8 Git

The workspace is not a Git repository at the root. Do not write commands or claims that assume commits/tags exist locally. The Indus agent itself has platform versions, which are separate.

### 22.9 Current HTML acceptance text

`FINAL-INTERVIEW-DECISION.html` correctly says four gates remain. If any future edit changes status, regenerate and verify `completion_audit.json` rather than manually painting a green status.

---

## 23. Scale-to-millions position

### 23.1 Safe claim

> The architecture is domain-configurable, not plug-and-play domain-ready. With authorized transcripts, business outcomes, policies, tool traces, and expert reviewers, the same control loop can be adapted to a bank, insurer, hospital, or contact center. Data adapters, domain contracts, evaluators, compliance rules, and infrastructure must be replaced or scaled; the core evaluate–diagnose–repair–gate loop remains.

### 23.2 Unsafe claim

> Upload one million SBI or LIC transcripts and this local system will directly improve the agent with minor changes.

### 23.3 What transcripts alone can do

- discover dialogue failure patterns;
- identify objections and language cohorts;
- estimate dispositions and escalation patterns;
- find repetition, factuality, and policy issues;
- create review queues and regression tests.

### 23.4 What transcripts alone cannot do

- prove payment settlement;
- prove tool effects;
- establish causal business lift;
- reproduce audio/channel failure if audio is absent;
- define compliance truth without policy/domain input;
- validate population representativeness by themselves.

### 23.5 Required enterprise-scale additions

- object store/data lake or warehouse;
- stream/batch ingestion;
- canonical trace schema;
- PII redaction/tokenization;
- access control, retention, and residency policies;
- payment/CRM/policy outcome joins;
- stratified/cohort sampling;
- active-learning human review;
- distributed scoring and caching;
- drift monitoring;
- multilingual calibration;
- executable tool/back-end sandbox;
- canary traffic allocation;
- alerting and rollback;
- experiment/prompt/model/config registries;
- recurring weekly operating cadence.

The first deliverable for a million-call corpus should be a reproducible baseline, failure taxonomy, evaluator calibration, opportunity map, and ranked experiment backlog—not an immediate prompt rewrite.

---

## 24. Interview narrative

### 24.1 Ten-point two-minute pitch

1. Real voice agents fail across conversation, execution, and audio—not only prompts.
2. I defined explicit task success and the controlled denominator for an EMI recovery call.
3. I collected 20 real Sarvam Indus calls and treated them as discovery evidence, not gold.
4. I built an EVA-inspired evaluator for task truth, experience, simulator validity, audio, and reliability.
5. Every failure becomes a packet with the first breaking event and component owner.
6. The repair router chooses manual prompt, GEPA, extractor, tool, workflow, or other fixes based on evidence.
7. I preserved negative candidates and used MLflow for lineage.
8. A strict release controller re-runs every candidate under the same evaluator and blocks per-case regressions.
9. V15 passed a sealed text final, and one real ElevenLabs-to-Samvaad realtime call proved the live evaluation path.
10. The final candidate remains held until one real tool effect and matched V12/V15 voice evidence pass the frozen gate.

### 24.2 Suggested demo sequence

1. Open Loopline overview and state the claim boundary.
2. Open the valid EVA live run.
3. Play 10–15 seconds of real audio.
4. Show the hidden caller goal/persona.
5. Show the explicit pay-now commitment.
6. Highlight Shubh’s redundant confirmation as the first defect.
7. Show EVA-A passed while EVA-X failed.
8. Show failure routing to prompt-owned terminal handling.
9. Show the GEPA candidate that scored high but was rejected for hard regressions.
10. Show V15’s sealed text result.
11. Show the empty/pending tool and matched voice gates.
12. End on promote/hold/rollback governance and the reusable domain-pack architecture.

### 24.3 Strong PM talking points

- “I separated measurement from optimization.”
- “I did not let the optimizer define truth.”
- “I preserved failed experiments.”
- “I found a ceiling effect and predeclared a non-TSR quality route.”
- “A task-success win can still be an experience failure.”
- “A transcript claim is not a tool side effect.”
- “Synthetic tests are for coverage; real voice is for transfer.”
- “The product is the release decision system, not a positive number.”
- “A hold or rollback can be the correct output.”
- “EMI is the reference adapter; the domain pack is the portability boundary.”

### 24.4 Questions likely in an interview

**Why not GEPA only?**

Because a prompt optimizer cannot define business truth, validate tools, repair runtime failures, or approve deployment. It is one repair arm.

**Why EVA?**

It provides the closest public reference for realtime simulated callers, simulator validation, and separate accuracy/experience scoring. We adapted its runtime to Samvaad.

**Why ElevenLabs if Sarvam is being evaluated?**

ElevenLabs is the independent realtime caller/simulator supported by EVA. Sarvam Samvaad remains the complete system under test.

**Why not a second Samvaad caller agent?**

Possible, but it would require another custom simulator provider and roughly two Samvaad sessions per test. ElevenLabs is a validated EVA caller path and preserves independence.

**Why not count no-answer calls?**

Connect rate is not controlled by the conversational policy under test. It should be monitored separately.

**Why is the 200-case set not final proof?**

It shares source traces and generation machinery, and its former held-out was inspected. It is useful development coverage, not independent evidence.

**Why is p=0.125 acceptable?**

It is not a significance claim. The result is bounded project evidence; final confidence requires matched live voice and larger repeated trials.

**Is the framework production-ready?**

No. It is an executable interview MVP with strong governance. Production requires outcome joins, enterprise security, distributed infrastructure, ongoing calibration, and canary operations.

**Would this work on one million transcripts?**

The control loop transfers, but ingestion, domain contracts, policy truth, outcome joins, sampling, privacy, and distributed evaluation must be adapted.

### 24.5 Final claim after all four gates

If and only if the live gate succeeds:

> I built a human-gated batch self-improvement framework for Sarvam Indus. A project-owned EVA-inspired evaluator measures multi-turn conversation, tool execution, voice experience, and reliability; a separate improvement engine proposes manual, GEPA, and component-level repairs; and an independent release controller re-evaluates every candidate and promotes only versions that pass exact regression and voice gates.

If the live gate fails, replace “promotes” with the actual hold/rollback result and explain the localized failure.

---

## 25. Definition of done

### 25.1 Truth is owned

- All critical real-call labels are owner-reviewed.
- Calibration is reported against owner truth.
- Provenance and uncertainty are visible.

### 25.2 Execution is real

- At least one live bot-to-bot path is captured. This is already true.
- At least one real live Indus tool path is captured. This is not yet true.

### 25.3 Comparison is fair

- Same scenario, state, simulator, acoustic condition, trial count, and evaluator across versions.
- Invalid simulator/provider sessions are excluded by rule.
- Per-case outcomes are available.

### 25.4 Gates are strict

- No aggregate score hides P0, safety, integrity, terminal-state, or preserved-win regressions.

### 25.5 UI tells the full chain

- metric → call → first break → family → owner → test → candidate → experiment → exact release decision.

### 25.6 Claim is bounded

- static diagnostic evidence, stateful text evidence, live voice evidence, and business outcomes remain separate.

---

## 26. Immediate continuation runbook for Claude Code

### 26.1 First actions in a new session

1. Read this file completely.
2. Read `FINAL-INTERVIEW-DECISION.html`.
3. Read `voice-agent-improvement/artifacts/framework/completion_audit.json`.
4. Read `voice-agent-improvement/artifacts/framework/verification/latest.json`.
5. Read `voice-agent-improvement/README.md`.
6. Run `python -m framework.verify` before editing current code.
7. Do not inspect or print `.env` values.
8. Do not run paid calls or mutate Indus without explicit authorization.

### 26.2 If Arnav asks “what should I do now?”

Answer in this order:

1. Confirm key rotation.
2. Review/version the 20 labels.
3. Fix the secure live tool route and capture one tool side effect.
4. Commit exact V15 in Indus.
5. Run three pilots.
6. Run the 18×2 matched voice suite.
7. Apply release gate.
8. Refresh Loopline and presentation.

### 26.3 If asked to fix tools

Read `INDUS-TOOL-CONNECTION.md` and current official Sarvam tool documentation. Do not invent endpoints or authentication shapes. Preserve fail-closed behavior.

### 26.4 If asked to deploy V15

Before touching Indus:

- hash candidate file;
- compare to frozen hash;
- present exact diff;
- confirm tool/auth state;
- confirm rollback version;
- ask for explicit authorization if not already given.

After commit:

- record actual Indus version;
- freeze the deployment mapping;
- do not alter prompt/config during matched evaluation.

### 26.5 If asked to run calls

Before execution:

- dry run;
- confirm provider keys exist without printing them;
- confirm credit/session budget;
- confirm record IDs;
- confirm app version;
- confirm tool route;
- require explicit live confirmation;
- run no automatic retries.

### 26.6 If asked to improve the UI

Do not fabricate data. Prioritize:

- real audio and transcript;
- exact first defect;
- provider evidence;
- tool timeline from real tool calls;
- state diff;
- baseline/candidate matched table;
- reliability and acoustic slices;
- failed-gate explanation;
- claim boundary.

Keep Loopline independent in branding while acknowledging EVA inspiration.

### 26.7 If asked for more GEPA

First check whether frozen live evidence identified a prompt-owned failure. If not, explain that optimizer volume is not evidence. If yes:

- move the failure into development under a new cycle;
- keep the current final untouched;
- version the candidate and evaluator separately;
- run GEPA with failure-specific feedback;
- retain all candidates;
- run strict regression and a new final protocol.

### 26.8 If a live result is negative

Do not patch the result in place. Preserve it, emit hold/rollback, localize the first defect, route it to an owner, and begin a new versioned loop.

### 26.9 Suggested continuation prompt

```text
Read /Users/Arnav/Claude/Projects/Sarvam/handoff.md completely, then inspect the current completion audit, verification result, V10 evaluator freeze, V15 prompt hash, and valid EVA live run. Do not print secrets, place paid calls, mutate Indus, or touch the sealed final. Report whether the four binding gates are still accurate and propose only the next safe action needed to close the live tool-effect gate.
```

---

## 27. Primary artifact index

Plan and narrative:

- `/Users/Arnav/Claude/Projects/Sarvam/FINAL-INTERVIEW-DECISION.html`
- `/Users/Arnav/Claude/Projects/Sarvam/FINAL-EXECUTION-REPORT.html`
- `/Users/Arnav/Claude/Projects/Sarvam/PRESENTATION-READY-COMPLETION-PLAN.html`
- `/Users/Arnav/Claude/Projects/Sarvam/SELF-IMPROVING-AGENT-FRAMEWORK.html`

Machine status:

- `voice-agent-improvement/artifacts/framework/completion_audit.json`
- `voice-agent-improvement/artifacts/framework/execution_manifest.json`
- `voice-agent-improvement/artifacts/framework/verification/latest.json`

Text evaluation and release:

- `voice-agent-improvement/artifacts/framework/emi/dynamic_release_v15.json`
- `voice-agent-improvement/artifacts/framework/emi/dynamic_release_gepa_finalist.json`
- `voice-agent-improvement/artifacts/framework/emi/selection.json`
- `voice-agent-improvement/artifacts/framework/emi/method_freeze.json`
- `voice-agent-improvement/artifacts/framework/emi/fresh_final_decision.json`

Evaluator and live suite:

- `voice-agent-improvement/artifacts/framework/emi/eva_adapter_v10/evaluator_freeze.json`
- `voice-agent-improvement/artifacts/framework/emi/eva_voice_suite_v1/manifest.json`
- `voice-agent-improvement/research/upstream/eva/data/emi_dataset.json`

Valid live evidence:

- `voice-agent-improvement/artifacts/eva_live/emi_eva_live_20260819_135630/`
- `dashboard/public/eva-live-run.json`

Tools:

- `voice-agent-improvement/framework/tool_service.py`
- `voice-agent-improvement/INDUS-TOOL-CONNECTION.md`

Candidate:

- `voice-agent-improvement/agent/candidates/v15-firm-today.md`

Tracking/UI:

- `voice-agent-improvement/artifacts/experiments/mlflow.db`
- `dashboard/app/page.tsx`
- `dashboard/public/dashboard-data.json`

Research/licensing:

- `voice-agent-improvement/UPSTREAM_SOURCES.md`
- `voice-agent-improvement/THIRD_PARTY_NOTICES.md`

---

## 28. Final handoff statement

The project should not be restarted. The sunk-cost audit has already happened, and the useful prior work survived because it became the improvement/governance control plane. EVA, τ-Voice, and VAmoS concepts supplied the missing dynamic voice, validity, reliability, and execution-truth layers.

The codebase is now at the point where additional architectural invention is less valuable than closing the four evidence gates. The most important next technical achievement is one authenticated live Indus tool effect. The most important owner achievement is reviewing the 20 provisional labels. The most important final experiment is the unchanged matched V12/V15 realtime voice suite.

The correct success condition is not “make V15 win.” It is:

> Run the frozen, fair evaluation; preserve every artifact; and let the independent release controller make the correct promote, hold, or rollback decision.
