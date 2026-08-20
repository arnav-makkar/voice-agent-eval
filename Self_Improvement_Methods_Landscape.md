# Self-Improvement Methods — Full Landscape & Recommended Stack

**For:** Sarvam AI pitch · **Companion to:** `Project_Plan_and_Architecture.md`
**Why this exists:** GEPA was one suggestion. This is the whole menu, compared — so the choice of engine is a reasoned portfolio, not a buzzword.

---

## The one idea a PM should lead with

**There is no single "best" method.** Self-improvement happens at distinct **layers** that differ on three axes:
1. **Does it touch model weights?** (prompt/memory = no; SFT/DPO/RL = yes)
2. **How much data/feedback does it need?** (a few traces vs. millions of labeled pairs)
3. **How fast & reversible is it?** (edit a prompt in seconds vs. a multi-day training run)

The best system is a **portfolio layered by cost and risk**: start where ROI is instant and reversible (no retraining), and **graduate only the proven wins** into weight-level updates on Sarvam's own sovereign models. The **eval engine is the flywheel** — every layer needs the same reward signal (did the agent achieve the objective?), so you build it once and feed all of them.

```
Layer 0  Eval & data engine        ── the substrate everything feeds on (not optional)
Layer 1  Prompt / instruction opt   ── no weights · cheap · fast · GEPA lives here
Layer 2  Memory / experience        ── no weights · agent remembers its own lessons
Layer 3  Self-critique / verifier   ── no weights · runtime guard on high-stakes turns
Layer 4  Weight updates (Sarvam)    ── SFT → DPO/KTO → RLVR · highest ceiling, highest cost
```

---

## Layer 0 — Eval & data engine (the substrate)

Not a "method" but the precondition for all of them: **simulated users + LLM-as-judge + failure mining/clustering**. Without a reward signal and a failure dataset, nothing can self-improve. This is Section 2–4 of the project plan. Build it first; it powers every layer below.

---

## Layer 1 — Prompt / instruction optimization (no weights · cheapest · fastest ROI)

Refine the **text** fed to the model — system prompt, per-intent instructions, tool-use policy, few-shot examples — without touching weights. This is where the demo's improvement number will mostly come from.

| Method | How it works | When to reach for it |
|---|---|---|
| **GEPA** (Genetic-Pareto) | A teacher LLM **reflects** on failing traces in natural language, rewrites instructions, and keeps a **Pareto frontier** of candidates that win on different clusters. Very sample-efficient. | Default for this project — rich textual failure feedback, few rollouts, avoids regressions. |
| **MIPROv2** (DSPy) | **Bayesian** joint optimization of instructions **+ bootstrapped few-shot demos**, in a propose-then-search loop. | The strong, well-supported **baseline** to benchmark GEPA against. |
| **TextGrad / LLM-AutoDiff** | Treats the agent as a computation graph; propagates **natural-language "gradients"** to fix each module. | Multi-module agents where you need **per-step credit assignment**. |
| **OPRO** | "LLM as optimizer" — generates and searches prompt candidates against a score. | Simple black-box improvement; good sanity baseline. |
| **APE / ProTeGi / ORPO-prompt / PromptBreeder / EvoPrompt** | Earlier or **evolutionary** prompt search (mutate, score, select). | Diversity / escaping local optima; mostly research-grade now. |

**Pick:** GEPA primary, MIPROv2 as the head-to-head baseline, TextGrad if the agent grows multi-module. All shipped in DSPy/MLflow.

---

## Layer 2 — Memory / experience (no weights · improvement persists at runtime)

The agent **accumulates lessons from its own history** and consults them on future calls — complements Layer 1 (which changes the static prompt; this adapts per situation).

| Method | How it works | When to reach for it |
|---|---|---|
| **Reflexion** | After a failed task the agent writes a **verbal self-reflection** into episodic memory ("verbal reinforcement"); reads it on the next attempt. No fine-tuning. | Long-tail intents; turning a single failure into an immediate next-try fix. |
| **ExpeL** | **Distills reusable insights/rules** from many past trajectories into a compact playbook the agent carries. | Converting thousands of calls into a few high-value heuristics. |
| **Memento** (case-based RL) | Learns a **retrieval policy** over a growing case bank — which past situations to reuse — without finetuning the LLM. | Continual adaptation when you can't/won't retrain. |

**Pick:** a Reflexion/ExpeL-style **"lessons learned" memory** the agent reads at runtime, so improvements stick between optimization runs.

---

## Layer 3 — Self-critique / verification at inference (no weights · runtime safety)

A check **before the agent commits** to a high-stakes action — the cheapest way to kill the *expensive* BFSI failures (wrong number, missed fraud-escalation).

| Method | How it works | When to reach for it |
|---|---|---|
| **Self-Refine** | Model critiques and revises its own draft answer before responding. | General quality lift on each turn. |
| **CRITIC** | Self-correction **grounded in tools** (verify a number against the API, not vibes). | Hallucination control in regulated answers (EMI, dues, policy). |
| **Verifier / judge gate** | A small model approves/blocks high-risk turns (e.g., "must escalate") before execution. | Compliance & escalation correctness — your heaviest penalties. |

**Pick:** a **verifier gate on high-stakes turns**. Directly attacks hallucination + escalation, the failures that actually cost money.

---

## Layer 4 — Weight updates (Sarvam-side · highest ceiling, highest cost)

Change the model itself. **Out of scope for a 1-month solo demo** (needs Sarvam's model + compute) but it's the strategic endgame — and it reuses the *same* eval signal you already built.

| Method | How it works | When to reach for it |
|---|---|---|
| **SFT on wins** (STaR / rejection sampling) | Fine-tune on the agent's **own successful trajectories**. | Bake proven behavior into the model cheaply. |
| **DPO / KTO / SimPO** (preference opt) | Train on **good-vs-bad pairs** mined from production. **KTO needs only a binary good/bad signal** — which your TSR judge already emits. | The clean bridge from eval → weights; cheap, stable, production-standard. |
| **GRPO / DAPO / RLVR** (verifiable-reward RL) | RL where a **programmatic check** scores success (task completed, correct tool result) — no human reward model. | Pushing the reasoning/tool-use ceiling. **Sarvam already uses RL in the Saaras ASR pipeline**, so this is in-house muscle. |

**The 2026 consensus pipeline:** SFT → DPO/KTO (alignment) → GRPO/DAPO with verifiable rewards (reasoning/tool-use). KTO is the natural first step because your eval already produces the binary signal it needs.

---

## Side-by-side

| Method | Layer | Touches weights? | Feedback it needs | Maturity / tooling |
|---|---|---|---|---|
| GEPA | 1 Prompt | No | Textual failure feedback | SOTA · gepa, DSPy, MLflow |
| MIPROv2 | 1 Prompt | No | Metric + val set | Mature · DSPy |
| TextGrad | 1 Prompt | No | Textual per-module | Active · TextGrad |
| OPRO | 1 Prompt | No | Scalar score | Research |
| Reflexion | 2 Memory | No | Verbal per-episode | Widely used |
| ExpeL | 2 Memory | No | Many trajectories | Research |
| Memento | 2 Memory | No (retrieval only) | Outcome reward | Research (2026) |
| Self-Refine / CRITIC | 3 Critique | No | Self / tool feedback | Widely used |
| SFT-on-wins | 4 Weights | Yes | Labeled successes | Standard |
| DPO / KTO / SimPO | 4 Weights | Yes | Good/bad pairs (KTO: binary) | Production-standard |
| GRPO / DAPO / RLVR | 4 Weights | Yes | Verifiable reward | Frontier post-training |

---

## Recommended stack

**For the demo (1 month, solo, no retraining) — buildable end-to-end:**
1. **Layer 0** — eval engine (simulated users + judge + failure mining). *Build first.*
2. **Layer 1** — **GEPA** as primary optimizer, **MIPROv2** as the benchmark baseline. *This drives the headline improvement number.*
3. **Layer 2** — a **Reflexion/ExpeL "lessons" memory** so gains persist at runtime.
4. **Layer 3** — a **verifier gate** on high-stakes turns to crush hallucination + bad escalation.

**For Sarvam (the roadmap slide, with their models + compute):**
5. **Layer 4** — mine production into **KTO/DPO** on Sarvam-M, then **RLVR/GRPO** where success is verifiable. Same eval signal, now moving weights. Ties directly to Sarvam's existing RL muscle and sovereign-model control.

**The flywheel:** one eval engine → feeds prompt-opt, memory, and weight-updates alike. That's the asset; the individual methods are interchangeable parts plugged into it.

---

## Sources
- Self-evolving / self-improving agent surveys: [Survey of Self-Evolving Agents (arXiv 2507.21046)](https://arxiv.org/pdf/2507.21046) · [Survey on Self-Evolution of LLMs (arXiv 2404.14387)](https://arxiv.org/pdf/2404.14387) · [self-improvement-llm review](https://github.com/Zesearch/self-improvement-llm)
- Prompt optimization: [GEPA (arXiv 2507.19457)](https://arxiv.org/pdf/2507.19457) · [Databricks — GEPA agents 90x cheaper](https://www.databricks.com/blog/building-state-art-enterprise-agents-90x-cheaper-automated-prompt-optimization) · [DSPy MIPROv2 & GEPA](https://oss.vicente.services/dspy.rb/optimization/prompt-optimization/) · [MIPROv2 (DeepEval)](https://deepeval.com/docs/prompt-optimization-miprov2) · [DSPy compilers](https://www.statsig.com/perspectives/dspy-compilers-prompt-optimization)
- Memory / experience: [Reflexion (arXiv 2303.11366)](https://arxiv.org/abs/2303.11366) · [Reflexion guide](https://www.promptingguide.ai/techniques/reflexion)
- Weight updates / post-training: [Post-Training in 2026: GRPO, DAPO, RLVR & Beyond](https://llm-stats.com/blog/research/post-training-techniques-2026) · [RLVR for enterprise LLMs (Appen)](https://www.appen.com/blog/rlvr)
- Voice-agent continuous improvement: [Maxim — human-in-the-loop continuous improvement](https://www.getmaxim.ai/articles/incorporating-human-in-the-loop-feedback-for-continuous-improvement-of-ai-agents/) · [Kore.ai — agentic voice 2026](https://www.kore.ai/blog/the-ai-voice-surge)
