# Third-party notices

The project studies the MIT-licensed repositories listed in `UPSTREAM_SOURCES.md`.

The project-owned `framework/` implementation is an independent implementation of published architectural ideas. The complete upstream repositories, including their original `LICENSE` and third-party notice files, are retained under `research/upstream/` for reproducibility.

## ServiceNow EVA adaptation

- Upstream: `https://github.com/ServiceNow/eva`
- Pinned commit: `e0041e3d9d4e706b21630a3ecb7595855004d63f`
- License: MIT; the upstream `LICENSE` remains in `research/upstream/eva/`.
- Project-owned addition: `research/upstream/eva/src/eva/assistant/samvaad_server.py`. The latest adaptation also adds deterministic caller-audio perturbations, per-trial correlation variables, isolated tool-state seeding/fetching, and execution-truth sidecars.
- Registration/config edits: `src/eva/orchestrator/worker.py`, `src/eva/models/config.py`, `configs/prompts/simulation.yaml`, `configs/prompts/judge.yaml`, and `src/eva/metrics/accuracy/faithfulness.py` inside the retained clone. The faithfulness adaptation exposes the initial scenario state to the judge because Samvaad grounds responses in deployment-time input variables rather than mandatory lookup tools.
- New fixtures: `configs/agents/emi_agent.yaml`, `data/emi_dataset.json`, `data/emi_scenarios/EMI-LIVE-001.json`, the frozen `EMI-VOICE-001` through `EMI-VOICE-018` suite, and `src/eva/assistant/tools/emi_tools.py`.
- Purpose: adapt EVA's documented Twilio-media assistant-server extension point to the official Sarvam Samvaad bidirectional CALL SDK while keeping the deployed Indus agent as the complete system under test.
- This adaptation is not an official ServiceNow or Sarvam distribution and does not imply endorsement.

If a future change copies or substantially derives an upstream file, add the source path, destination path, pinned commit, license, copyright notice, and modification summary here before distribution.
