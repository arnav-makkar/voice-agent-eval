# Sarvam AI — Voice & Speech Intel Brief (mid-2026)

> Built for Aryan's pitch to join Sarvam as an AI Product Manager.
> Focus: voice agents, ASR/TTS, B2B/voice products. Confidence tags: **[Confirmed]** = multiple sources or Sarvam's own site, **[Reported]** = 2026 press, **[Gap]** = couldn't confirm, go find it.
>
> ⚠️ **THIS FILE WAS WRITTEN BEFORE VERIFICATION.** `sarvam-dossier.html` is the corrected source of truth — see its Fact-check tab. The critical corrections are patched in below, but where this file and the dossier disagree, **the dossier wins.**
>
> 🔴 **AND IT IS NOW PRE-EPOCH.** Sarvam held its first Epoch conference on **30–31 July 2026** and reframed itself from a model lab into a horizontal platform. Everything below describes the company as of ~24 July. **Read the dossier's ★ Epoch update tab first** — it supersedes this file wherever they conflict.

---

## 0.5 What changed at Epoch, 30–31 July 2026

**The positioning.** The founders' own words at the press briefing: *"We have established Sarvam more as a platform player. We want to be a horizontal platform player where people can build."* Full stack — infrastructure, foundation models, enterprise agents, developer tools — competing with hyperscalers, not only with frontier labs. **[Reported — Business Today, 30 Jul 2026]**

**New and confirmed on sarvam.ai:**

- **Model Training as a service** — managed fine-tuning, **reinforcement learning and evaluation**, customer owns the delivered weights, training data isolated and kept in India. LoRA "Adaptation" and full-weight "Specialisation," plus a frontier co-build research engagement. **[Confirmed]**
- **Sarvam Code** — long-running coding agent with a steerable plan, checkpoint recovery, per-task model routing, and **billing only for completed work**. **[Confirmed]**
- **Sarvam Inference** — India-hosted inference service. **[Confirmed]**
- Products nav gained Model Training and Sarvam Code. **Kaze is still absent from it.** **[Confirmed]**

**Announced, press-sourced:** a **1T+ parameter model** from scratch within six months (coding, cybersecurity, scientific research, simulation); **Epoch Builder Edition** (7B and 70B models on 2T tokens, 10+ Indian languages — private preview Aug 2026, GA Q4 2026); **Saaras V4** and **Saaras V4 Multi-Speaker** (simultaneous-speaker transcription; adds Odia, Sanskrit, Manipuri); **Bulbul V4** (emotional TTS — laughter, excitement, emphasis); Vision commercially launched for document intelligence; **~2,000 NVIDIA Blackwell GPUs today, targeting 10,000**, plus an HCLTech sovereign data centre in Odisha; **500+ customers with the bulk of revenue from the private sector, not government**; voice and chat models claimed **5–10× cheaper** than frontier equivalents; **Devendra Singh Chaplot** (ex-xAI) hired; pilots with three IITs and two state governments. **[Reported]**

**Not announced:** anything about Kaze, any eval/observability product, any SEA or Africa expansion. **[Gap]**

### The two that hit this pitch

1. **Sarvam now sells evaluation** — as a bespoke services engagement attached to custom model training, with acceptance criteria agreed during scoping. It does **not** score objective completion inside a live Samvaad call, and nothing feeds failures back automatically. Reframe the pitch from *"build eval"* to *"productize the eval you already deliver by hand, and push it into the runtime."*
2. **Sarvam already ships outcome-based billing** on Sarvam Code. Drop "no competitor can offer per-outcome pricing." Say instead: *"You already bill for completed work on Code. Samvaad still bills for minutes. TSR is the unit that lets you bill Samvaad the same way."*

### Numbers in this file that are now wrong or unsafe

| Claim | Correction |
|---|---|
| "$0.80 per million tokens" (post-Epoch reporting) | **Not on any Sarvam page.** Published: 105B ₹4 in / ₹16 out per 1M; 30B ₹2.5 / ₹10. |
| Samvaad "₹3.5 per minute" | **No voice-agent line item exists on the price sheet.** Conflicts with an earlier Inc42 "from ₹1/minute." Quote no per-minute figure. |
| Sarvam Edge "688MB" | Sarvam's own claim is **"under 1GB."** 688MB is the sum of their component sizes (Saaras 294 + Mayura 334 + Bulbul 60), not a figure they publish. |
| India AI Impact Summit dates | **16–20 February 2026** (PIB). PM inaugurated 19 Feb. Neither "16–17" nor "18–19" was right. |
| Kaze "available May 2026" | Never launched, never announced, no price, no product page, not mentioned at Epoch. |
| "No one is titled CEO" | Still true **on Sarvam's own site** — but The Hans India (28 Jul 2026) styles Pratyush Kumar "co-founder and CEO." Phrase it as "no CEO title on Sarvam's own site." |

### Added 3 Aug 2026 — the evaluation-honesty thread

**This is the strongest thing in the whole folder.** The most persistent public criticism of Sarvam is not that its models are bad — it's that nobody can verify they're good.

- **Forbes, 7 Mar 2026** (Janakiram MSV), *"India Can Train A Sovereign Model But Still Cannot Prove It Works."* Section heading: **"Every Performance Claim Is Self-Reported."** No HuggingFace Open LLM Leaderboard entry, no Arena ranking, no arXiv paper with methodology or peer review. IndiVibe, Sarvam's Indic benchmark, was **"designed by Sarvam, translated by Sarvam and judged by Gemini on Sarvam-selected prompts."** **[Confirmed — read in full]**
- **NextBigWhat, 31 Jul 2026**, the Epoch reaction piece: builders questioned whether "the benchmark slides [were] selective," noted "missing or conveniently ranked competitors," and said the conversation has moved to **"evaluation honesty, actual capability versus packaging."** Best line: *"The speech work is solid and didn't need the questionable comparison graphs. Don't spend the goodwill on theatre."* **[Confirmed]**
- **Sarvam's own blog, 2 Apr 2026** — *"Evaluating Indian Language ASR."* Their last publication before Epoch, and it's a 14-minute technical guide to eval. They have a layered metric stack and have **open-sourced two repos**: `github.com/sarvamai/llm_wer` and `github.com/sarvamai/llm_intent_entity`. **[Confirmed]**

**The bigger find — Sarvam forked NVIDIA NeMo Gym on 28 May 2026.** `github.com/sarvamai/Gym` is a fork of `NVIDIA-NeMo/Gym` (GitHub API: `fork: true`, parent `NVIDIA-NeMo/Gym`). NeMo Gym is *"a library for evaluating and improving models and agents using environments,"* and it defines an environment as **dataset + agent harness + verifier (task completion scoring) + state** — and exists to *"seamlessly transition between evaluation, agent optimization, and training."* **That is the project plan's architecture, with NVIDIA's name on it.** Apache 2.0, 1,083 stars, 252 forks, upstream actively developed.

Sarvam's fork: created 28 May 2026, last pushed 5 Jun 2026, 0 stars, issues disabled. **Could not determine whether Sarvam wrote their own code in it** — the commits/branches endpoints returned nothing. Say "they forked it," not "they're building on it." **[Confirmed via GitHub API]**

**So build the BFSI agent as a NeMo Gym environment,** with a verifier that computes TSR. Three consequences: the demo becomes something a Sarvam engineer can clone and *run*; the vocabulary shifts from "eval harness" to **environment** and **verifier**, which is their language now; and Layer 4 gets a concrete path, since NeMo Gym integrates with NeMo RL, Unsloth and VeRL. **Risk to raise yourself:** someone at Sarvam may already be doing this — ask.

**⚠ Licence catch:** GitHub returns `license: null` for **both** `llm_wer` and `llm_intent_entity`. Public but all-rights-reserved by default, despite the blog calling them "open source." **Depend on them, don't vendor them.** NeMo Gym is Apache 2.0 and is clean to build in.

**Repo detail:** `llm_intent_entity` — 62 stars, 19 forks, 5 open issues, ships `prompt_template.txt` (their actual judge prompt), needs a GCP service account with Vertex AI. Entry point is `process_dataset_for_intent_entity_evaluation()` per the README — **the blog shows a different signature (`evaluate()`); trust the README.** Install path `cd llm_evaluation/llm_intent_entity` reveals a bigger internal `llm_evaluation` monorepo that isn't public. `llm_wer` — 25 stars, 12 forks, 5 open issues.

**Their metric stack, and where the pitch plugs in:**

| Their metric | What it measures | Your move |
|---|---|---|
| **Intent Score** (binary 0/1, LLM judge) | Did the system capture what the speaker was trying to say? Threshold: 100% pass | **TSR is this one rung up.** Theirs scores the utterance, yours scores the call. Say exactly that. |
| **Entity Preservation Score** (0–1, ≥0.90) | Names, places, numbers, dates transcribed correctly. They name **banking** as a primary use case | Your BFSI hallucination flag *is* an entity failure. Use their metric name and threshold. |
| **LLM-WER / LLM-CER** (<15%) | WER rescored by an LLM so colloquial variants and code-mix script choices stop counting as errors | Replace raw WER in the metric spine. Their own example: a bank's code-mixed Hindi bot "looks 15% worse than it is" on raw WER |
| **COMET** (>0.80) | Translation quality, secondary to Intent Score | Skip unless demoing translate mode |

**Adopt their reproducibility checklist verbatim** — temperature=0, pin the judge model version (never `latest`), seed where supported, version-control prompts and log a (prompt + model version) hash with every result, structured JSON judge output, 2–3 few-shot examples per language, and a fixed **50-sample calibration set** re-run on any judge change with a 1-percentage-point drift threshold. Put it on screen and attribute it to them.

**A fourth product idea — the sovereign judge.** Both Sarvam eval repos use **Gemini via Google Vertex AI** as the judge, and Forbes made the same observation about IndiVibe. A sovereign-AI company currently outsources the judging of its own quality to a US frontier model, and every eval call leaves the country. The product: Sarvam 30B fine-tuned for evaluation, scoring on the same stack that serves. Pitch gently — it's a gap, not a hypocrisy.

**Tone warning.** Sarvam-M (May 2025), post-trained on Mistral Small, drew a public pile-on — Deedy Das called it embarrassing, others called it a wrapper on a French base; Sridhar Vembu defended them. Forbes frames the 105B as "in part, a strategic correction." **Come in as an ally, never as an auditor.** "You published the metric stack, I extended it" works. "Your benchmarks aren't verified" does not.

**Also new:** **Chanakya** (fully on-prem AI system for defence/intelligence/national security) · **Anvaya** (custom 30B for defence and government) · **Sarvam Work** (enterprise agent, Slack or on-prem) · Vision 2.0 (Indian handwriting OCR) · a **San Francisco research lab**, with Chaplot joining as an **advisor**, not a hire · Epoch was also **"in association with AWS"** · Enterprise Day's themes were *"architecture to own, operate, and improve it"* and *"The ROI Rethink — AI creates more value over time as every workflow, interaction and decision helps improve the system"* — quote that back to them · the **BFSI panel ran first** on Enterprise Day · **SBI Life goes nationwide this month**: 80M customers, 350k distributors · Kaze was **demoed** at Epoch but not launched (correcting the 31 Jul note above) · Sarvam annual revenue ~**₹29 crore ($3.5M)**.

---

**Samvaad, from Sarvam's own product page as of 31 Jul 2026:** 100M+ conversations cumulative, 11 languages, <500ms latency, <24 hours to deploy, claimed 10× ROI vs IVR. Platform-wide: 10B+ tokens served, <100ms median latency, 99.9% uptime SLA. Customer wall now shows **Aadhaar, Axis Bank, CRED, CRED Resolve, Decentro, IDFC, IndiaMART, Infosys, LIC, Mahindra Finance, NABARD, SBI Life, Skill India, Tata Capital, Urban Company** — over half BFSI, which argues the BFSI anchor choice for you. New case studies: **SBI Life** (millions of policy calls, 10+ languages) and **Skill Development India** (50,000+ farmer feedback calls, Maharashtra).

---

## 0. Bottom line

Sarvam is now India's **sovereign-AI unicorn** ($1.5B), and voice is its sharpest commercial edge. Its conversational platform **Samvaad** runs **2M+ interactions/day** (doubling roughly every 2 months) across banking, insurance, govtech and defence. They have the full stack — ASR (**Saaras v3**), TTS (**Bulbul**), LLM (**Sarvam-105B / Indus**), agents (**Samvaad**), on-device (**Edge**) — all built and hosted in India.

**The wedge for your pitch:** Sarvam sells voice agents at massive scale but, like everyone in the category, has no public story for **proving each agent actually achieved its objective** and **automatically getting better from its own failures**. That's exactly the "self-improving voice agents" brief the hiring team handed you. You're not pitching a feature — you're pitching the reliability layer a voice company at this scale structurally needs.

---

## 1. The company right now

| Item | Detail | Confidence |
|---|---|---|
| Stage | India's newest AI unicorn, ~June 2026 | [Reported] |
| Funding | **$234M first close of a $300M Series B**, ~$1.5B post-money. **HCLTech led with $150M** (10.46% stake), with **Bessemer**; existing backers **Khosla Ventures, Peak XV** continuing. ⚠️ **Lightspeed led the 2023 Series A and is NOT named in the Series B.** (Series A was $41M, Dec 2023.) | [Confirmed] |
| Co-founder | **Dr. Pratyush Kumar** — IIT Bombay, PhD ETH Zürich, ex-IBM Research / Microsoft Research / IIT Madras / AI4Bharat. | [Confirmed] |
| Co-founder | **Dr. Vivek Raghavan** — DPI / Aadhaar biometrics, ~12 yrs UIDAI; PhD CMU. | [Confirmed] |
| ⚠️ **CEO** | **NO ONE IS PUBLICLY TITLED CEO.** Sarvam's Series B page, About page and Pratyush's own LinkedIn all use **"Co-founder"** only. Only third-party databases (Tracxn) say CEO. **Never use a CEO title in the pitch.** | [Verified — corrected] |
| Lead PM | Not public. **Find on LinkedIn / via your hiring contact before the pitch.** | [Gap] |
| Legal entity | Axonwise Private Limited, Bengaluru | [Confirmed] |
| Mission | "AI for India" — full-stack, sovereign, built+deployed+governed entirely in India; selected under the **IndiaAI Mission** to build India's foundational LLM. | [Confirmed] |

---

## 2. The product lineup (from sarvam.ai)

**Products:** Samvaad (voice/conversational agents) · Studio · Akshar · Arya · Indus (105B consumer app) · **Edge (on-device)**
**APIs:** Text-to-Speech · Speech-to-Text · Doc Digitisation · Translation · Dubbing · Models

Two that matter for you specifically:
- **Samvaad** — the thing your project should plug into (details below).
- **Edge** — on-device models. This is the thread to pull for your glasses/AR ambition: AR glasses need low-latency, offline, sovereign voice. Sarvam already has the edge piece.

---

## 3. The voice / speech stack (what you'd be improving)

### Saaras v3 — ASR / speech-to-text (their core listening model)
- **~19% WER on IndicVoices** (v2.5 was ~22%); covers **22 official Indian languages + English**. [Reported]
- Output modes: transcribe, translate, verbatim, transliterate, codemix.
- **Native streaming** for low-latency partial transcripts; trained on **1M+ hours** of real Indian speech via a 4-stage pipeline (pretrain → SFT → **RL** → post-training for long-tail errors). [Reported]
- Saarika (older ASR) is being deprecated in favour of Saaras v3 `transcribe` mode.
- Scale: **500K+ hours of audio transcribed/month.** [Reported]

### Bulbul — TTS (their speaking model)
- Contact-centre-grade voices, **11 Indian languages + English**, sub-second.

### Samvaad — the conversational agent platform (your integration target)
- Voice + WhatsApp + web agents, **11 Indian languages**, **sub-500ms latency**, multi-agent orchestration, **cross-channel memory** (voice ↔ WhatsApp ↔ web).
- Connects to **CRM, core banking, payment systems**; handles appointment booking, payment follow-ups, cart recovery, collections, inbound support.
- Build flow: dashboard to create agents → define intents/flows → attach knowledge bases + transactional APIs → test in playground → deploy. Deploy options: Sarvam Cloud / private VPC / on-prem. Pilot-to-prod in <24h.
- **Going self-serve:** Sarvam is opening Samvaad beyond enterprise to startups/SMBs/developers (free tier + paid). Translation: a flood of new, less-curated agents → **even more need for automated eval + self-improvement.** That's your tailwind.

### Sarvam-105B / Indus — the brain
- 105B **MoE** (128 experts, ~10.3B active params, 128k context), trained from scratch on **12T tokens** using **4,096 NVIDIA H100 SXM GPUs** under the IndiaAI Mission (Yotta Shakti Cloud, per press), **22 languages**, **Apache 2.0** (weights on HF + AI Kosh). Consumer app **Indus**. Sarvam-30B trained on 16T tokens. [Confirmed] ⚠️ *Do not say "1,000+ H100s" — that understates their compute 4×.*

---

## 4. Real B2B clients & use cases (your pitch ammunition)

Anchor every demo to one of these — it proves you understand their actual book of business:

- **Tata Capital** — Samvaad across **consumer loan products**: multilingual engagement, **sentiment detection, escalation to humans**. (Lending/collections.) [Reported]
- **Ministry of Agriculture & Farmers Welfare** — voice-agent data-collection campaign across **17M farmers**. (Govt scale.) [Reported]
- **Razorpay** — partnership for **voice-first conversational commerce + payments** in Indian languages. [Reported]
- **Govts of Odisha & Tamil Nadu** — AI compute facilities. [Reported]
- Priority verticals stated by Sarvam: **banking, insurance, govtech, defence, healthcare.**

**Best demo anchor:** a **loan-collections / payment-reminder agent in Hindi** (mirrors Tata Capital) — high stakes, clearly measurable objective ("did the customer commit to pay / complete the action?"), and exactly where a wrong answer costs money. Perfect for a hard task-success metric.

---

## 5. Where this points your project (the strategic read)

Your hiring brief = **self-improving voice agents**. Here's the spine, grounded in the research:

**Step 1 — Quantify objective completion.** For each conversation, did the agent achieve its goal? This is **Task Success Rate (TSR)** — the industry north-star; production target is **85%+**. Everything else (containment >70%, first-call-resolution >75%, tool-call success >99%, hallucination <2% / 0% in regulated, WER <10%, barge-in recovery >90%, latency P50<1.5s) is **diagnostic** — it explains *why* TSR is where it is. Your "60% → 75%" arc is literally moving TSR.

**Step 2 — Find the break point.** Run the agent over thousands of simulated + real conversations, then locate the **exact turn where it goes wrong** (mis-transcription, wrong intent, bad tool call, hallucinated policy, failed escalation). This transcript-level failure mining is the heart of the demo.

**Step 3 — Self-improve with GEPA.** **GEPA (Genetic-Pareto)** — from **Databricks + UC Berkeley (2025)** — does **reflective prompt evolution**: the LLM reads its own failing trajectories *in natural language*, diagnoses them, and mutates the agent's instructions, keeping a Pareto front of high-performers. Databricks reports **state-of-the-art enterprise agents ~90x cheaper** this way, and it's shipped in **MLflow as `GepaPromptOptimizer`**. It beats RL while being far more sample-efficient — which is the whole point of "self-improving without retraining the model." This is your engine, and you can cite a real company (Databricks) already running it in production agents.

**The loop you'll build & demo:**
`run agent on eval set → score TSR + diagnostics → mine failure turns → GEPA reflects & rewrites prompt/flow → re-run → TSR 60% → 75%.`
Do it end-to-end on one Sarvam-shaped use case, in an Indian language, and you've shown you can implement a voice agent, evaluate it, diagnose it, and make it improve itself — the entire AI-PM-who-can-build story.

---

## 6. The competitive / technical landscape you'll build against

**Voice-agent platforms (know these cold — they'll ask):**
- **ElevenLabs Agents** — full-stack, best-in-class TTS, RAG, BYO-LLM, ~sub-300ms. The voice-quality leader.
- **Vapi** — orchestration layer (mix any STT/LLM/TTS), **62M calls/month, 99.99% SLA**, ~$0.05/min + provider costs. The developer/flexibility leader.
- **Bolna** — **India-first**, low-cost (~$0.04/min), more assembly required. Sarvam's closest local-flavour comparison; **Bolna already lists Sarvam as a transcriber provider** — useful framing.
- Others in the arena: Retell, Bland, Deepgram, Telnyx.

**Eval is now its own tooling category** (Hamming, Cekura, Maxim, Bluejay) — meaning the market agrees eval is the missing layer. Sarvam building this *natively into Samvaad* (not bolting on a third-party) is a credible PM thesis.

**Sarvam's positioning vs. all of them:** sovereign + Indian-language depth + full-stack + on-device (Edge). They don't compete on being a US orchestration layer; they compete on *India, owned end-to-end*. Frame your self-improvement layer as **what makes a sovereign voice platform trustworthy at govt/BFSI scale** — not as copying Vapi.

---

## 7. Open intel gaps to close before the pitch

1. **Lead PM's name + background** — [Gap], find on LinkedIn / ask your hiring contact.
2. **Confirm CEO vs. co-founder titles** (Pratyush vs. Vivek) — don't address the wrong person.
3. **Exact current Samvaad pricing tiers** for the self-serve launch (was being rolled out).
4. **Whether Sarvam already has any internal eval/observability** for Samvaad — if yes, position as *augment*, not *replace*.

---

## Sources
- Sarvam Series B / unicorn: [sarvam.ai/announcing-series-b](https://www.sarvam.ai/announcing-series-b) · [TechCrunch](https://techcrunch.com/2026/06/15/sarvam-becomes-indias-newest-ai-unicorn-with-234-million-funding-round-led-by-hcltech/) · [Business Standard](https://www.business-standard.com/technology/artificial-intelligence/hcltech-sarvam-ai-investment-sovereign-ai-policy-india-126061701260_1.html)
- Samvaad voice agents: [sarvam.ai/products/conversational-agents](https://www.sarvam.ai/products/conversational-agents) · [Inc42](https://inc42.com/buzz/exclusive-sarvam-ai-to-open-voice-ai-agents-platform-for-public-use/) · [Elets BFSI](https://bfsi.eletsonline.com/sarvam-ai-opens-voice-ai-platform-sarvam-samvaad-to-public-targets-wider-adoption/)
- ASR Saaras v3: [sarvam.ai/blogs/asr](https://www.sarvam.ai/blogs/asr) · [docs.sarvam.ai — Saaras](https://docs.sarvam.ai/api-reference-docs/models/saaras)
- Clients (Tata Capital, MoA, Razorpay, govts): [Bessemer](https://www.bvp.com/news/sarvam-ai-building-sovereign-ai-for-india) · [Razorpay × Sarvam](https://www.business-standard.com/technology/tech-news/razorpay-sarvam-ai-partnership-voice-based-online-shopping-payments-126032400389_1.html)
- Leadership: [sarvam.ai/about-us](https://www.sarvam.ai/about-us) · [Business Today](https://www.businesstoday.in/technology/news/story/meet-the-minds-behind-sarvam-ai-how-pratyush-kumar-and-vivek-raghavan-are-building-indias-sovereign-ai-stack-515472-2026-02-10)
- Sarvam-105B / Indus: [sarvam.ai/blogs/sarvam-30b-105b](https://www.sarvam.ai/blogs/sarvam-30b-105b) · [Business Standard](https://www.business-standard.com/technology/tech-news/sarvam-105b-model-sovereign-ai-india-foundation-model-launch-impact-summit-126021900551_1.html)
- GEPA: [GEPA paper (arXiv 2507.19457)](https://arxiv.org/pdf/2507.19457) · [Databricks blog — 90x cheaper agents](https://www.databricks.com/blog/building-state-art-enterprise-agents-90x-cheaper-automated-prompt-optimization) · [gepa-ai/gepa](https://github.com/gepa-ai/gepa)
- Voice eval metrics: [Hamming — metrics guide](https://hamming.ai/resources/voice-agent-evaluation-metrics-guide) · [Cekura](https://www.cekura.ai/blogs/voice-ai-evaluation-metrics)
- Platform comparison: [Retell — Vapi vs ElevenLabs](https://www.retellai.com/blog/vapi-vs-elevenlabs) · [Bolna — Sarvam transcriber](https://www.bolna.ai/docs/providers/transcriber/sarvam)
