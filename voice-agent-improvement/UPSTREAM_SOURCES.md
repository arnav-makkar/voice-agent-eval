# Upstream research sources

These repositories are pinned research references. Product code lives under `framework/`; it does not import or represent itself as an official distribution of any upstream project.

| Source | Pinned commit | License | What we use |
|---|---|---|---|
| [ServiceNow EVA](https://github.com/ServiceNow/eva) | `e0041e3d9d4e706b21630a3ecb7595855004d63f` | MIT | Runtime base for the realtime ElevenLabs user simulator and assistant-server contract. We add a project-owned Samvaad server class, EMI domain fixture, and registration/config changes inside the retained clone. |
| [Sierra tau benchmark](https://github.com/sierra-research/tau2-bench) | `a2c024725189473d2d7cea3a5cfdbcc67478e41f` | MIT | State-equivalent task success, environment assertions, action/tool checks, communicate checks, user-simulator and voice-perturbation concepts. |
| [Veris Riley agent](https://github.com/veris-ai/riley-agent) | `a22e0e96e68778c16761e05ebd2d3931d713f525` | MIT plus upstream notices | Provider/transport and isolated backend patterns linked from the VAmoS paper. The VAmoS benchmark platform itself is not public; our execution-truth harness is independently implemented and described as VAmoS-inspired. |

## Modification policy

- Keep research clones under `research/upstream/` for inspection and reproducibility.
- Pin commit hashes before comparing behavior.
- Prefer project-owned, domain-agnostic contracts over importing a large upstream runtime.
- Preserve the original copyright and license notice in any substantially derived file.
- Do not imply ServiceNow, Sierra, or Veris endorsement.
- Record copied or materially adapted files in `THIRD_PARTY_NOTICES.md` before release.

## Papers and datasets

- EVA paper: https://arxiv.org/abs/2605.13841
- EVA benchmark dataset: https://huggingface.co/datasets/ServiceNow-AI/eva-bench
- EVA audio/results dataset: https://huggingface.co/datasets/ServiceNow-AI/eva
- tau-Voice paper: https://arxiv.org/abs/2603.13686
- VAmoS paper: https://arxiv.org/abs/2607.27453
