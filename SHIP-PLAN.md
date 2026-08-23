# SHIP PLAN — from "v4 committed" to "ready to shoot"

Planned on Fable (max). Execute on Opus 5 (max). Follow workstreams in order;
each has acceptance checks. Nothing here spends credits except where marked
**[CREDITS — ask first]**. Nothing here places phone calls; the owner records.

State at planning time (verified):
- v4 **committed** on Indus = generation 2, sha `667ce12e2626c75e`, 15,347 chars.
- `.env` → `SARVAM_APP_VERSION=4` (done; harnesses read it).
- Tunnel + tool service healthy. Dashboard JWT ~8h. Clock synced (23/24-08).
- Rollback: v3 seed + CHAMPION.json on disk.

---

## WS-1 · Audio evidence (feeds the site; do first)

### 1a. Bot-to-bot MP3s — already local, just stage them
Sources (v3 baseline pilots, `audio_mixed.wav` in each):
```
artifacts/eva_live/emi_eva_live_20260822_175829/records/EMI-BENCH-0001   pay-now
artifacts/eva_live/emi_eva_live_20260822_182942/records/EMI-VOICE-002   future-promise
artifacts/eva_live/emi_eva_live_20260822_183340/records/EMI-VOICE-003   callback
artifacts/eva_live/emi_eva_live_20260822_183651/records/EMI-VOICE-004   refusal
artifacts/eva_live/emi_eva_live_20260822_184426/records/EMI-VOICE-005   dispute
```
→ ffmpeg to mp3 (128k) → `dashboard/public/evidence/audio/bot-v3/{slug}.mp3`.
Also emit `dashboard/public/evidence/audio/bot-v3/index.json`:
`[{id, slug, title, scenario_id, duration_s, tools, disposition, eva_a, eva_x, transcript:[{speaker,text}], audio:"/evidence/audio/bot-v3/x.mp3"}]`
(pull transcript + ledger + EVA from `artifacts/campaign2/bot_to_bot/pilot_5.json`).

**Accept:** 5 mp3s playable; index.json fields non-null; total size < 8 MB.

### 1b. Indus call-logs API discovery (recordings + transcripts for the 15 phone calls)
This also sets up human-tier EVA (WS-5).
1. Browser pane (logged in) → `https://indus.sarvam.ai/samvaad/monitor/agent-analytics/call-logs?appId=EasyCredit--4e112b0d-9931&channelType=v2v`.
2. Arm the XHR/fetch hook **before** the page data loads (pattern used for
   text-chat + authoring discovery). Capture: list endpoint, per-call detail,
   transcript, recording URL. Open ONE call's detail to trigger detail routes;
   click its audio player once to capture the media URL shape.
3. Write `voice-agent-improvement/scripts/fetch_call_logs.py`:
   - list calls for the app over 22–23 Aug (phone tier: 15 baseline calls on v3);
   - match to cards by start-time order (see `artifacts/campaign2/phone/*.json`;
     `calls_01_05.json` has `recorded_at`);
   - save per call: `artifacts/campaign2/phone/recordings/card-NN.json`
     (transcript + metadata) and `card-NN.mp3` (recording);
   - copy mp3s → `dashboard/public/evidence/audio/phone-v3/` + `index.json`
     (same schema as 1a; eva_a/eva_x null for now; verdict/tools from
     `baseline_15.json` per_card).
   - Auth: dashboard JWT from `.env.local`. Retry on the intermittent TLS timeout.
**Fallback (recordings not exposed):** transcripts-only → index.json with
`audio: null`; site player shows transcript with a "recording unavailable" note.
Do NOT fake audio.

**Accept:** ≥1 real recording verified audible before batch; 15 JSONs saved;
mapping card↔call listed for owner sanity-check (times + durations table).

---

## WS-2 · Loopline website update (the big one)

Everything data-driven where possible. The c2 view loads
`public/story.campaign2-preview.json` + `public/calls.campaign2-preview.json`.

### 2a. Regenerate story JSON from artifacts — `scripts/export_story_c2.py` (new)
Read: REFLEX-RESULT.json, family_ladder.json, noise_probe.json,
invariant_audit.json, reflex_ladder.json, pilot_5.json, phone/baseline_15.json,
chat_bulk/{v3c,g1c,g2c,v3cb,g1cb,g2cb,v3p,g2p,abl}_*.jsonl.
Emit acts (schema in `app/page.tsx` — conform to `Story`/`Act` types):
- **measure**: three-tier baseline. phone 9/15; bot EVA-A .678/EVA-X .600 (n=5,
  caveats); chat 98/180 env (88 strict), blind 33/60; noise floor (flip 2.2%,
  σ60 0.82) — measured BEFORE any candidate.
- **diagnose**: failure classes with counts (wrong-code 16, escalate-missing 13,
  fptp-for-maybe 12, promise-missing 11, check-missing 11); invariants P=1.00
  R=0.28; the one-sentence thesis: *says the right thing, fails to write it down*.
- **improve** (NEW architecture act): the Reflex loop — sense → distill →
  search → gate → deploy; two-component candidate {instructions, exemplars};
  GEPA + merge + severity-weighted trainset; reflector gemini-3.1-pro-preview;
  explore→consolidate; stuck bucket; 1,570 conversations; machine-only lineage
  statement; gen-1 section growth table (Tools +711, Closing +593, Objective
  +564); gen-2 = instructions unchanged, +1 rule +1 mined exemplar → already_paid
  7→11.
- **reevaluate**: the ladder (98→155→160 env / 88→135→141 strict; blind
  33→57→59; fresh-blind 18→27→29; guardrails 40→62→63; words/turn 15.9→15.6);
  McNemar (+62/−0, p≈0; g1→g2 p=0.18 stated as NOT established); paraphrase
  (29→26 vs 18→17, ~82% survives); ablation (33→49→59: second component = 38%
  of gain); invariants 23→2.
- **seal** (instrument audit): stale-clock incident → auto-sync + regression
  tests; token-expiry contamination → purged + re-run; exemplar-copying
  hypothesis → falsified by experiment. Framing: *the evaluator was audited as
  hard as the agent*.
- **decide**: gate verdicts; v4 committed (sha); voice transfer = the open gate;
  S7 protocol (5 bot canary [CREDITS], then 15 human cards, hang-up column).
- still_open: voice unmeasured; conditional_promise_trap 4/12; compounding
  p=0.18; judges designed-not-built; single account/scripted callers.
- headline: before 54.4% → after 88.9% (env, suite), repairs 62, regressions 0.
Numbers ONLY from artifacts — the script asserts each figure it emits.

### 2b. Calls JSON + audio evidence UI
- Read `app/Calls.tsx` first; conform `calls.campaign2-preview.json` to its
  types; add fields: `tier` ("phone"|"bot"), `audio` (url|null), `transcript`.
- New component `AudioEvidence` (in Calls.tsx or `app/Audio.tsx`):
  - **dropdown (`<select>`) to choose a call**, grouped: "Bot-to-bot · v3
    baseline (5)" / "Phone · v3 baseline (15)" / placeholders "· v4 (after S7)";
  - selected call renders: `<audio controls preload="none">`, verdict pill,
    tools-fired chips, disposition, collapsible transcript;
  - loads the two index.json files at runtime; missing audio → transcript-only
    with note.
- Add nav/link card to `/evolution.html` ("Prompt evolution — the diffs").

### 2c. Contrast + section pass (owner asked: "clearly visible, clear contrast")
- Audit `globals.css`: body text uses --ink-2 (#4A4740 on #E9E6E0 ≈ 7.4:1, ok);
  fix any --ink-3 used for *reading* text (≈4.4:1 — keep for labels only);
  bump `.note`/small text to --ink-2; check dark theme equivalents.
- Ensure every act renders as a clearly separated section (existing pattern);
  verify new improve/reevaluate acts don't collapse when arrays empty.
### 2d. Verify (browser)
- `preview_start loopline-dashboard` → `/?view=c2`; screenshots light+dark;
- dropdown: select a bot call → audio request 200, plays (network check);
  select phone call (or fallback note path);
- console: zero errors; no horizontal overflow at 375px;
- data spot-check: 6 numbers on screen == artifact values (list them in log).

---

## WS-3 · Prep the owner's recording session (15 phone calls on v4)

1. `place_phone_call.py`: confirm it reads SARVAM_APP_VERSION (=4) or pass
   explicitly; verify AGENT_VARIABLES still match v4's declared set (25 vars —
   diff against `stored_agent_variables()`); clock-fresh assert before each call.
2. Add `--dry-run` flag: prints the full payload + SAY-THIS-DATE lines for a
   card without placing the call. Dry-run card 1 and card 3 (relative-date card)
   and check dates derive from today's clock (23-08), not stale text.
3. Refresh `CALL-SHEET.html`: header "TESTING v4 (generation 2)"; re-derive any
   absolute dates that cards instruct the caller to say (card 2/3/4) from the
   current clock; add per-card checkbox column **"agent hung up unaided? Y/N"**
   (defect P6 — only measurable by phone). Republish the artifact (same URL).
4. Recording-day runbook block at the top of the call sheet:
   tool service up → tunnel 200 → clock fresh → cards in order 1–15 →
   after each call, wait for my grade before the next (journal isolation).
5. Grading path: verify the per-card journal check used for baseline_15 runs
   unchanged against v4 (dry pass on existing baseline data).
**Accept:** two dry-runs printed correct payloads; call sheet republished;
owner needs only: start recorder, run cards, mark hang-up column.

## WS-4 · Bot-to-bot v4 preflight (no spend until go)

1. Verify the 5 EVA records still pinned to the live account and today-valid
   dates (EMI-BENCH-0001, EMI-VOICE-002..005: expected promise 28-08 still
   future ✓; callback tomorrow ✓; `current_date_time` 2026-08-23 == today ✓).
2. ElevenLabs caller via API: turn_timeout 2.0, turn_eagerness normal,
   first_message "", voice Aman, llm qwen36-a3b, max 120s.
3. Confirm `run_eva_samvaad_live.py` resolves app_version from env (=4).
4. `scripts/preflight_s7.sh` — one command, prints all checks + the 5 exact
   run commands. **[CREDITS — ask first]** ~25 credits for the 5 calls; run only
   on the owner's explicit go, ideally BEFORE the phone session (canary).
**Accept:** preflight all-green; commands printed; zero credits spent.

## WS-5 · Human-tier EVA groundwork (via WS-1b transcripts)

- If transcripts land: `scripts/human_tier_eva.py` — map card transcripts into
  the chat-tier judged metrics we can honestly compute without audio
  (task_completion from journal [exists], plus transcript-derived words/turn and
  progression heuristics). Full EVA judged panel (faithfulness etc.) = STRETCH:
  wire only if EVA's metrics processor accepts transcript-only records without
  surgery; otherwise mark "prepared, not run" in the story JSON — do not
  hand-wave scores.
- Label clearly on site: human-tier EVA = partial (no turn_taking; no simulator
  fidelity — real humans are ground truth).

## WS-6 · Docs sync (fast, last)

- RUNBOOK.html: S6 outcome block → corrected ladder (98→160, blind 33→59,
  +62/−0, gate PROMOTE, v4 committed w/ sha); S7 → "in progress: canary + 15
  cards". Mark REFLEX-RUN.html "COMPLETED" banner with final numbers.
- PRESENTATION-LOG.md: append v4-committed entry (sha, time) + link to site.
- Memory: update `loopline-project-state` (v4 committed = gen2; ladder; what
  S7 needs) — single edit.

---

## Order & time (machine)
1. WS-1a (10m) → WS-1b discovery+fetch (45–60m)
2. WS-2a export script (40m) → 2b UI (60m) → 2c contrast (15m) → 2d verify (20m)
3. WS-3 (30m) → WS-4 (15m) → WS-5 (20–40m if transcripts) → WS-6 (15m)
Total ≈ 4–4.5h. Owner time afterwards: 5 bot calls go/no-go, then ~60m recording.

## Hard rules for the executor
- No candidate text edited, ever. v4 stays byte-identical (sha check before
  bot-to-bot and before phone grading).
- No credits without an explicit go in chat. No phone calls placed by scripts
  unless the owner runs them.
- Every number on the site traceable to an artifact file; the export script
  asserts, it does not type constants.
- Site works with audio missing (fallback path tested), both themes, 375px.
- Intermittent apps.sarvam.ai TLS timeouts: retry ×3 w/ backoff, never
  conclude from a timeout.
