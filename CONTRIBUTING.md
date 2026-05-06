# Contributing to DeepThought

Thank you for your interest in contributing to DeepThought.

---

## Before You Start

Read the [AI-Guided Onboarding →](BKM_ONBOARDING.md) first.
Most questions about how the system works can be answered by pasting
the prompts there into Claude or Copilot.

---

## Ways to Contribute

### 1. Add a Domain Pack

The easiest and most valuable contribution. No Python required.

Create `domains/<your_domain>/` with:
- `specialists/*.md` — four reviewer roles for your domain
- `domain.yaml` — embedder, collections, calibration config
- `calibration.json` — run `scripts/run_dimension_analysis.py` to generate
- `bkm.md` — domain-specific lessons learned

See `domains/linux_x86/` as the reference implementation.
See [VECTORDB_GUIDE.md](VECTORDB_GUIDE.md) for corpus preparation.

### 2. Fix a Bug or Improve the Core Engine

`core/deepthought_equation.py` is the TVA math engine.
`agents/` contains the LLM pipeline.
`vectordb/` contains the embedding and search layer.

Run tests before submitting:
```bash
pytest tests/ -v
```

### 3. Improve Documentation

All docs have three language versions (English / 繁體中文 / 简体中文).
If you update one, please update all three.

### 4. Report Issues

Open a GitHub issue with:
- What you tried
- What you expected
- What happened
- Your domain and corpus size

---

## What We Don't Need

- Fine-tuning scripts or model weight contributions
- New LLM provider integrations (use `.env` to configure existing ones)
- Changes to the TVA math without empirical validation

---

## Pull Request Process

1. Fork the repo
2. Create a branch: `git checkout -b your-feature`
3. Make your changes
4. Run tests: `pytest tests/`
5. Commit with a clear message
6. Open a PR against `main`

Keep PRs focused. One change per PR.

---

## Questions

Before opening an issue, ask Claude or Copilot with the context from
[BKM_ONBOARDING.md](BKM_ONBOARDING.md). The AI can answer most
domain adaptation and setup questions without involving the maintainer.

---

*Licensed under Apache-2.0. See [LICENSE](LICENSE).*
