# Loopline: self-improving voice-agent framework

Loopline is an executable interview MVP for evaluating, diagnosing, improving, and governing conversational agents. Sarvam Indus EMI recovery is the validation domain; the learning loop is case-agnostic.

The repository keeps three jobs separate:

1. **Evaluation** runs versioned multi-turn scenarios against isolated tool/state environments and scores deterministic task truth, guardrails, experience, and first failure. A Gemini Pro semantic judge is secondary.
2. **Improvement** routes failures to prompt, extractor, tool, workflow, knowledge, model, channel, or human-policy repairs. Manual candidates and native GEPA Optimize Anything are independent arms.
3. **Release governance** compares exact paired outcomes, rejects severe regressions, freezes the selected method, opens a group-separated final once, and leaves voice deployment to an explicit human gate.

All EasyCredit data is fictional. Credentials remain in `.env`; the exported dashboard is redacted and intended for local use.

## Final evidence

| Evidence | V12 | Selected v15 | Decision |
|---|---:|---:|---|
| 30-case stateful development suite | 16/30 (53.3%) | 30/30 (100%) | 14 repairs, zero task regression; eligible for fresh final |
| 12-case sealed fresh final | 5/12 (41.7%) | 9/12 (75%) | 4 repairs, zero task regression; pass text final, await matched voice |

- Fresh-final exact paired p = 0.125. It is diagnostic, not a statistical-significance claim.
- v15 final experience = 0.9375 versus 1.0 baseline, within the predeclared 10-point floor.
- Fresh-final semantic diagnostics: faithfulness 3.833 → 4.000, conciseness 4.000 → 4.000, progression 3.833 → 3.750; no factual, integrity, or forbidden-behavior violations. Deterministic state/action checks control release.
- Native stateful GEPA produced a 28/30 finalist. The gate rejected it for one P1 state regression and one P0 guardrail regression.
- The six-condition Sarvam CALL acoustic diagnostic recognized pay-now intent in 6/6 conditions and exposed redundant V12 confirmation in 6/6. It is baseline component evidence, not a matched v15 voice A/B or voice TSR.
- The earlier latency-corrected voice retry is preserved as provider HTTP 402 infrastructure evidence. Credits were later replenished; the remaining blockers are a secure live tool route, an exact V15 commit, and the frozen matched round.
- Cash settlement is not observable. The current business proxy is verbal pay-now commitment.
- One preserved live EVA–Samvaad V12 run now has the full six-component score: EVA-A 1.00 (pass), EVA-X 0.667 (fail), overall 0.833. The task succeeded, but turn-taking and progression each scored 0.5 because the agent overlapped/reconfirmed after commitment.
- Evaluator V10 freezes the next prospective protocol: 12 core scenarios, 6 deterministic acoustic-risk scenarios, the isolated live tool service, guarded provider-session runner, exact paired release gate, and a default-off synthetic tool-auth mode for controlled evaluation environments. V10 changes the prospective caller name to just “Arnav”; no matched V12/V15 live result exists yet.

The 20 real V12 calls are discovery evidence with provisional labels, not gold or causal proof. The older 200-row failure-derived corpus is a development-only static next-turn diagnostic library; its legacy held-out split is compromised and excluded from final claims.

## Run the evidence UIs

Loopline dashboard:

```bash
cd /Users/Arnav/Claude/Projects/Sarvam/dashboard
npm run dev
```

Open `http://localhost:3000`.

MLflow:

```bash
cd /Users/Arnav/Claude/Projects/Sarvam/voice-agent-improvement
source .venv/bin/activate
mlflow ui --backend-store-uri sqlite:///artifacts/experiments/mlflow.db --port 5000
```

Open `http://localhost:5000`.

## Verify everything

```bash
cd /Users/Arnav/Claude/Projects/Sarvam/voice-agent-improvement
source .venv/bin/activate
python -m framework.verify
python -m framework.pipeline status
python -m framework.pipeline report
python -m framework.pipeline export-dashboard
```

`framework.verify` reruns Python tests, dashboard lint/tests/build, frozen-hash checks, final-protocol checks, and a credential-pattern scan. The latest timestamped result is `artifacts/framework/verification/latest.json`.

`python -m framework.completion_audit` writes the plan-level acceptance record to `artifacts/framework/completion_audit.json`. It keeps owner/external gates open rather than converting implemented harnesses into evidence passes.

## Primary artifacts

1. `artifacts/framework/emi/dynamic_release_v15.json` — 30-case paired development gate.
2. `artifacts/framework/emi/dynamic_release_gepa_finalist.json` — rejected stateful GEPA arm.
3. `artifacts/framework/emi/selection.json` — independent arm selection.
4. `artifacts/framework/emi/method_freeze.json` — frozen prompt/evaluator/suite hashes.
5. `artifacts/framework/emi/dynamic_scenarios_v1/fresh_final_seal.json` — final-set seal.
6. `artifacts/framework/emi/fresh_final_decision.json` — once-only final decision.
7. `artifacts/framework/emi/voice_stress_v1/live/voice_summary.json` — baseline acoustic diagnostics.
8. `artifacts/framework/execution_manifest.json` — hash-linked stakeholder manifest.
9. `../FINAL-EXECUTION-REPORT.html` — final interview narrative and demo script.
10. `artifacts/framework/emi/eva_adapter_v10/evaluator_freeze.json` — frozen live evaluator, transport, tool-state and 18-scenario voice protocol.
11. `artifacts/framework/emi/eva_voice_suite_v1/manifest.json` — prospective record IDs, source contracts and dataset hash.
12. `INDUS-TOOL-CONNECTION.md` — exact remaining Indus API-tool connection procedure.
13. `artifacts/framework/completion_audit.json` — machine-readable status of every phase in `FINAL-INTERVIEW-DECISION.html`.

Do not commit v15 into Indus or place new calls without action-time approval. After approval and sufficient credits, deploy the exact frozen prompt, record a matched caller-card voice round, apply the same hard gate, canary, and rollback policy.

## Run the frozen prospective voice suite

Configuration-only dry run (no voice sessions):

```bash
research/upstream/eva/.venv/bin/python scripts/run_eva_samvaad_suite.py \
  --app-version 12 --suite core --trials 1 --max-sessions 12 --dry-run
```

After the real Indus API tools are attached and an exact V15 is committed, run
the identical suite for each version. The wrapper requires an explicit session
budget and live confirmation. For reliability, set the same `--trials` value
for both versions; EVA emits pass@1, pass@k and pass^k.

```bash
research/upstream/eva/.venv/bin/python scripts/run_eva_samvaad_suite.py \
  --app-version 12 --suite all --trials 1 --max-sessions 18 --confirm-live-suite
research/upstream/eva/.venv/bin/python scripts/run_eva_samvaad_suite.py \
  --app-version 15 --suite all --trials 1 --max-sessions 18 --confirm-live-suite
```

Then apply the predeclared exact gate:

```bash
python scripts/compare_eva_samvaad_suites.py \
  --baseline artifacts/eva_matched_live/<v12-run-id> \
  --candidate artifacts/eva_matched_live/<v15-run-id>
```

## EVA live caller → Samvaad

The genuine realtime bot-to-bot path uses an ElevenLabs Agents caller named
Arnav against the complete deployed Shubh Samvaad agent. The guarded wrapper
runs one record, one trial, and one attempt; it never retries a paid provider
session automatically.

```bash
research/upstream/eva/.venv/bin/python scripts/run_eva_samvaad_live.py --dry-run
research/upstream/eva/.venv/bin/python scripts/run_eva_samvaad_live.py --confirm-live
```

Artifacts are written under `artifacts/eva_live/<run_id>/`. Provider billing,
credential, and transport failures are invalid infrastructure attempts and are
excluded from agent-quality scoring.

## Research provenance

- [ServiceNow EVA](https://github.com/ServiceNow/eva): stateful episode evaluation and Accuracy × Experience separation.
- [τ-Voice](https://arxiv.org/abs/2603.13686): matched acoustic perturbations, reliability, and latency semantics.
- [VAmoS](https://arxiv.org/abs/2607.27453): isolated state, transcript + tool execution truth, assertion graders.
- [GEPA Optimize Anything](https://gepa-ai.github.io/gepa/blog/2026/02/18/introducing-optimize-anything/): bounded full-episode prompt search.

Pinned upstream commits and licenses are recorded in `UPSTREAM_SOURCES.md` and `THIRD_PARTY_NOTICES.md`. The implementation is described as inspired/adapted, never endorsed by upstream authors.
