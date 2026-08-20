# Self-improving voice agent — executed plan

## Product objective

For connected EMI-recovery calls, maximize the share of eligible callers who explicitly agree to open the official app and pay now. A future promise, callback, refusal, dispute, already-paid claim, or safe escalation can be the correct terminal outcome, but none is counted as primary conversion.

The system is “self-improving” only as a governed loop:

```text
new calls → immutable/redacted traces → deterministic + human-calibrated scoring
          → exact first breaking turn → ranked failure clusters
          → fix routed to prompt, extractor, runtime, product, or policy owner
          → candidate search → regression/safety gate → human approval
          → matched voice round → promote, hold, or rollback → repeat
```

GEPA owns one step: prompt candidate search. It is not the corpus, evaluator, deployment system, or proof of voice improvement.

## Phase 1 — Freeze real voice evidence · complete

- Selected 20 usable V12 Sarvam Indus calls from the raw attempt history.
- Locked 15 matched benchmark calls and 5 exploratory stress calls.
- Joined attempts and transcripts by platform identifier and project `run_id`.
- Removed contact and audio URL fields before writing analysis artifacts.
- Preserved failures; did not replace bad agent behavior with convenient wins.

Artifacts: `artifacts/baseline/calls.jsonl`, `artifacts/baseline/corpus.json`, `improvement/baseline_selection.json`.

## Phase 2 — Human gold labels and trace evaluator · complete

Every call records eligibility, primary success, correct task outcome, severity, integrity/safety status, failure owner, and the first observable breaking turn. Deterministic logic separately finds the first payment ask, explicit commitment, repeated confirmation, disposition mismatch, and summary corruption.

Frozen V12 result:

- 20 total calls: 15 matched + 5 exploratory.
- 10 eligible matched calls; 9 explicit pay-now commitments; primary TSR = 90%.
- Matched task success = 86.67%.
- Disposition accuracy = 86.67%.
- Hard safety violations = 0%.
- Integrity violations = 26.67%.
- Redundant confirmation = 40%.
- Evaluator agreement with this human-labelled slice = 100% on primary and task success.

The release gate fails. High TSR does not override integrity or disposition defects.

Artifacts: `improvement/human_annotations.json`, `artifacts/baseline/scorecards.jsonl`, `artifacts/baseline/summary.json`.

## Phase 3 — Mine and route failures · complete

Ten clusters were ranked by recurrence, severity, and business impact. Repeated confirmation is the dominant prompt failure (6 calls). Other prompt-owned breaks include dispute precedence, one-turn trust resolution, conditional-check conversion, AI-refusal handling, late-charge accuracy, unsupported completion wording, unavailable-app loops, and interruption recovery.

The invalid `fraud_claim` disposition is extractor-owned, not prompt-owned. It is fixed in a separate output-variable patch so the optimizer cannot claim credit for it.

Artifacts: `artifacts/baseline/failure_clusters.json`, `agent/candidates/gepa-v13/OUTPUT-VARIABLES.md`.

## Phase 4 — Freeze the scenario contract library · complete

The local library contains 150 TV-only synthetic task contracts: 90 development, 30 regression, and 30 held-out. It uses τ²-inspired hidden state and task contracts plus MatrAIx-inspired behavioral fields. It is not τ² benchmark-compatible, does not contain MatrAIx data, and is not counted as real voice evidence.

The contracts support cheap text simulation and regression coverage. Fixture transcripts validate pipeline mechanics only; they must never be used to claim model improvement.

Artifacts: `dataset/scenarios-v2.jsonl`, `dataset/DATASET-SPEC.md`, `dataset/audit_corpus.py`.

## Phase 5 — GEPA candidate search · complete offline

GEPA 0.1.4 ran a bounded candidate search over ten evidence-derived policy contracts. The release harness compares the seed and complete V13 patch, then evaluates an adversarial aggressive-collection stress control as a required rejection.

- V12 prompt policy coverage: 20%.
- Selected V13 prompt policy coverage: 100%.
- Aggressive pressure variant: rejected.
- Claim boundary: this is prompt-contract coverage, not voice TSR.

V13 changes are narrow: terminal commitments end immediately; disputes beat wrong-party; trust is resolved with one official-app micro-close; unavailable channels and repeated AI refusal stop looping; outstanding amount wording respects the ledger.

Artifacts: `artifacts/optimization/lineage.json`, `agent/candidates/gepa-v13/SYSTEM-PROMPT.md`, `agent/candidates/gepa-v13/RELEASE-CHECKLIST.md`.

## Phase 6 — Experiment lineage and monitoring · complete

MLflow 3.15 stores the V12 metrics, candidate score, prompt hashes, evidence artifacts, and claim boundary in a local SQLite backend. Loopline reads a redacted dashboard snapshot and provides:

- CXO metrics and release gate;
- all 20 calls with filters;
- full turn-level traces;
- exact first breaking-turn highlights;
- ranked failure clusters linked back to calls;
- GEPA candidate lineage and policy cases; and
- pipeline state through the pending matched voice round.

The browser receives no Sarvam key. `improvement.live_sync` refreshes analytics server-side and exports only redacted data.

## Phase 7 — Human approval and matched V13 voice round · next

1. Review the candidate prompt and output extractor patch.
2. Paste both into an uncommitted Indus draft; confirm Shubh, opening, TV variables, tools, and Genie warnings.
3. Commit V13.
4. Record the same 15 hidden caller cards using `MT-CAND-01` through `MT-CAND-15` in the counterbalanced order in `CALL-RECORDING-GUIDE.html`.
5. Keep behavioral failures. Replace only platform errors, missing transcripts, or unusable audio.
6. Import and score V13 without changing labels, acceptance thresholds, or denominators.

## Final decision rule

Promote V13 only if paired voice evidence improves primary TSR or preserves it while materially reducing integrity/repetition defects, with no new P0 safety regression. Otherwise hold or rollback and route the new first-break clusters into the next cycle.

At millions of weekly calls, the same logic adds sampling, drift detection, confidence-based human review, cohort slices, canaries, access control, alerting, and rollback. This MVP proves the control logic and artifacts without claiming production scale.
