# Phase 1 — TV EMI recovery data curation

## The honest dataset claim

This project defines **150 synthetic TV EMI-recovery task contracts**. A contract is not a transcript. A transcript exists only after the frozen agent proxy and an isolated caller simulator have completed a rollout.

The final experiment is paired: the same 150 contracts run once against frozen v10 and once against the final candidate. That produces 300 synthetic text transcripts. Synthetic text results and real Indus voice-call results are always reported separately.

## Why τ² is used, and exactly how

We use the useful experimental structure from τ², not the package or benchmark dataset. Every local scenario contains:

1. a public environment and ledger available to the agent;
2. a private user goal and behavioral state available only to the caller simulator;
3. a conversion rule and terminal conditions;
4. an objective success contract; and
5. reproducibility fields: version, seed, and contract hash.

This makes the conversations stateful and verifiable instead of asking one model to “make up a realistic transcript.” The artifact must be described as **τ²-inspired**, not τ²-compatible.

## Why MatrAIx is used, and exactly how

MatrAIx is not a runtime dependency and no MatrAIx record is copied into this corpus. We use only a narrow behavioral schema inspired by its persona framing:

- preferred language;
- digital confidence;
- trust in official apps;
- patience;
- interruption tendency;
- verbosity; and
- communication style.

Ability to pay, objection, and conversion threshold live in the private task state rather than the persona. This prevents a large persona description from overwhelming the causal test. Every record says `source: synthetic_local` and explicitly says it is not a MatrAIx record or representative population data.

## Coverage grid

All cases use the same product: **Samsung 55-inch 4K Smart TV** purchased through the fictional Croma/EasyCredit demo ledger.

| Dimension | Values | Cases per value |
|---|---:|---:|
| Delinquency state | pre-due, 6 days overdue, 20 days overdue | 50 |
| Recovery intent | 10 | 15 |
| Communication style | 5 | 30 |
| Behavioral profile | 30 | 5 |
| Total contracts | — | 150 |

The ten intent families are four payment-now conversion cases, a future-date promise, a callback, a hard refusal, already paid, transaction dispute, and wrong party. No no-answer scenarios are generated because connect rate is outside the agent's control and outside this experiment.

Splits are deterministic and balanced:

- development: 90;
- regression: 30;
- held-out: 30.

The optimizer may see development examples. Regression protects capabilities during iteration. Held-out is not inspected or optimized against before final benchmarking.

## Transcript generation protocol

For each selected scenario:

1. Render the frozen opening message from public runtime inputs.
2. Give the caller simulator the persona, ledger truth, private intent, objection, ability to pay, and conversion rule.
3. Give the agent proxy only the frozen candidate prompt, public runtime inputs, and visible conversation.
4. Alternate one caller turn and one agent turn for at most six agent turns.
5. Stop on payment-ready acceptance, promise date, callback, refusal, already-paid claim, dispute, wrong party, disconnection, or max turns.
6. Store every utterance, candidate prompt hash, scenario hash, models, seed, latency, and token usage returned by the provider.

The caller starts uninterested and does not volunteer hidden information. `payment_ready` requires explicit agreement to open/login to the official app and pay now. “I will see later” and generic promises do not count.

The simulator's terminal state is not the final score. Phase 2 adds deterministic checks and an independent diagnostic judge. This avoids letting the same model generate a behavior and declare itself successful.

## Generation modes

### Fixture mode

Fixture mode creates deterministic scripted rows to test files, hashes, turn ordering, and downstream code. Every row contains:

```json
"benchmark_evidence": false
```

Fixture rows must never appear in TSR results or the CXO claim.

### Model mode

Model mode uses two isolated roles through an explicitly configured OpenAI-compatible `/chat/completions` service. Keep the caller model and version frozen for all paired runs. The agent proxy model must also remain fixed; only the candidate prompt changes.

Recommended experiment discipline:

- use a strong fixed caller simulator;
- use one fixed agent-proxy model for v10 and candidate comparisons;
- set temperature to `0.2` and record the seed;
- use a different model or deterministic rules for evaluation;
- rerun malformed JSON, but never delete genuine agent failures;
- manually review 12 of the 120 development/regression baseline rollouts before optimization.

## Commands

Build the 150 contracts:

```bash
cd /Users/Arnav/Claude/Projects/Sarvam/voice-agent-improvement
python3 dataset/generate_scenarios.py
wc -l dataset/scenarios-v2.jsonl
```

Smoke-test ten rows without an API or model cost:

```bash
python3 -m dataset.generate_transcripts \
  --provider fixture \
  --limit 10 \
  --output dataset/transcripts/fixture-v10.jsonl \
  --overwrite

python3 -m dataset.audit_corpus \
  --scenarios dataset/scenarios-v2.jsonl \
  --transcripts dataset/transcripts/fixture-v10.jsonl
```

Generate model-based development rollouts after selecting a provider and models:

```bash
export SIM_LLM_API_KEY='...'
export SIM_LLM_BASE_URL='https://your-provider.example/v1'
export SIM_CALLER_MODEL='gpt-5-mini-2025-08-07'
export SIM_AGENT_MODEL='gpt-5-mini-2025-08-07'

python3 -m dataset.generate_transcripts \
  --provider openai-compatible \
  --split development \
  --candidate-id indus-v10 \
  --output dataset/transcripts/model-v10-development.jsonl
```

Repeat separately for regression. Do not run or inspect held-out until the final candidate has been frozen.

The pinned GPT-5 mini snapshot is the recommended first run because it supports Chat Completions and structured output, is inexpensive, and will not silently change between v10 and v11. The two roles remain context-isolated even when they use the same model snapshot. The evaluator in Phase 2 must be deterministic or use a different model; it cannot be this simulator declaring its own success.

## Phase 1 exit gate

Phase 1 is complete only when:

- 150 contracts pass balance, arithmetic, provenance, leakage, and uniqueness checks;
- 90 development and 30 regression v10 model rollouts exist;
- all rollouts contain trace metadata and valid alternating turns;
- 12 stratified rollouts have a written human QA decision;
- failures remain in the corpus; and
- the 30 held-out contracts remain uninspected by prompt optimization.
