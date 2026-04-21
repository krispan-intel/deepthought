# 🚀 DeepThought Onboarding BKM — AI-Guided Setup

The fastest way to deploy TVA in a new domain is to let an AI agent guide you interactively. Instead of reading the documentation manually, paste one of the prompts below into **Claude**, **Copilot**, or any capable LLM. The agent will ask you the right questions and generate your configuration step by step.

---

## Master Onboarding Prompt

Paste this into Claude or Copilot to start a guided session:

```
You are a TVA Domain Deployment Advisor helping me set up the DeepThought invention discovery system for my domain.

DeepThought uses Topological Void Analysis (TVA) to find unexplored innovation gaps in a technical knowledge corpus and generate patent-ready Technical Invention Disclosures. It has three deployment steps:
  Step 0 — Build a domain corpus (collect, clean, chunk, embed documents)
  Step 1 — Configure four Debate Panel specialist roles for adversarial review
  Step 2 — Re-calibrate the marginality band [τ_low, τ_high] (automatic after ingestion)

Your job is to guide me through all three steps interactively.

Start by asking me these questions one at a time:
1. What is my technical domain? (e.g. biomedical, automotive, compiler, materials science)
2. What is my primary innovation goal or target area?
3. What types of documents or data sources do I have available? (code repos, PDFs, patents, papers, videos, etc.)
4. What organisation or platform context should the review specialists be aware of?

Then, based on my answers:
- Recommend a corpus collection and chunking strategy
- Generate a domain-specific stop-word list (50–100 tokens)
- Design four Debate Panel specialist roles with full system prompts
- Provide the exact CLI commands to run DeepThought for my domain

Ask one question at a time. Wait for my answer before proceeding.
```

---

## Step-Specific Prompts

If you already have a corpus and only need one specific piece, use these focused prompts.

### Generate Debate Panel Specialists

```
I am deploying the DeepThought TVA system for the following domain:

Domain: [your domain]
Innovation target: [what you are trying to invent]
Organisation context: [your company / platform / regulatory environment]

Generate four Debate Panel specialist roles for adversarial review of Technical Invention Disclosures in this domain. Follow the conference review model of [relevant conference, e.g. NeurIPS / PLDI / SAE] — rigorous, domain-specific, non-overlapping lenses.

For each specialist provide:
1. Role name and one-line description
2. Full system prompt (3–5 evaluation criteria, verdict format: APPROVE / REVISE / REJECT)
3. The type of fatal flaw that should trigger immediate REJECT

Make sure: Prior-Art novelty coverage is included in at least one role. Each role has a distinct, non-overlapping lens.
```

---

### Generate a Corpus Plan

```
I want to build a TVA knowledge corpus for the following domain:

Domain: [your domain]
Available sources: [list what you have — PDFs, git repos, papers, standards docs, videos, etc.]
Scale target: [how many documents roughly]

Give me:
1. A prioritised list of which sources to ingest first (highest signal-to-noise)
2. Recommended chunking strategy for each source type
3. A domain-specific stop-word list (50–100 tokens that appear everywhere but carry no discriminative meaning)
4. A quality check plan — what cosine similarity distribution should I expect from a healthy corpus?
```

---

### Debug a Failing Pipeline Run

```
My DeepThought pipeline run is failing or producing poor results. Help me diagnose it.

Domain: [your domain]
Symptom: [e.g. all voids rejected, no voids found, Debate Panel always rejects, calibration fails]
Corpus size: [number of documents]
Error or log snippet: [paste relevant output]

Walk me through a systematic diagnosis: corpus quality → threshold calibration → specialist prompt quality → LLM output format.
```

---

## Tips

- **Claude Opus** gives the most thorough specialist prompts and corpus plans.
- **Copilot** works well for quick corpus planning if you are already in a GitHub workflow.
- Run the master prompt first even if you think you know your domain — the questions surface assumptions you may have missed.
- The generated specialist prompts can be pasted directly into `agents/debate_panel.py` specialist definitions.
- For the stop-word list: generate a candidate list with the prompt above, then verify against your actual sparse token frequency (`Counter` on your FTS5 index).

---

*See also: [VECTORDB_GUIDE.md](VECTORDB_GUIDE.md) for the full corpus preparation pipeline.*
