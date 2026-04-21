# Innersource Migration Checklist

Pre-flight checklist before moving this repo to Intel innersource.

---

## 🔴 Must Fix (before push)

- [ ] **`configs/settings.py` line 23** — hardcoded internal IP `10.67.114.161:3001/v1`  
  → Replace default with `""` and require via `.env`

- [ ] **`.env.example` line 6** — hardcoded internal IP `10.67.116.243:3001/v1`  
  → Replace with `http://your-internal-llm-endpoint:3001/v1`

- [ ] **Verify `.env` is not staged** — `git status` should not show `.env`  
  (currently confirmed clean, but double-check before push)

---

## 🟡 Review Before Push

- [ ] **`output/generated/`** — contains real TID drafts, audit JSONs, human_review HTML  
  → Decide: exclude via `.gitignore`, or clean the folder before push

- [ ] **`output/` root** — `CXL_FLC_TID_Revised.json`, `HardIRQ_Cookie_TID_Revised.json`, etc.  
  → These are real void outputs. Keep locally, exclude from innersource if sensitive.

- [ ] **`logs/`** — may contain run history with internal model names or endpoints  
  → Add to `.gitignore` if not already

- [ ] **`data/`** — `data/vectorstore/`, `data/raw/` likely too large and sensitive  
  → Should be in `.gitignore` already; confirm before push

---

## 🟢 Already Clean

- [x] `.env` is gitignored — real keys never committed
- [x] `.env.example` uses placeholder values (except the IP above)
- [x] `kris.pan@intel.com` in PAPER.md — fine for innersource, it's the author credit
- [x] `expertgpt.intel.com` in `.env` only — not in committed code
- [x] No gh CLI / Claude CLI tokens in any committed file
- [x] All secrets (`ANTHROPIC_API_KEY`, `GITHUB_TOKEN`) are placeholders in `.env.example`

---

## 📋 Nice to Have

- [ ] Add `CONTRIBUTING.md` — how others can run the pipeline internally
- [ ] Confirm `README.md` Quick Start commands work on a clean Intel machine
- [ ] Check if `scripts/start_service.sh` has any hardcoded paths

---

*Last updated: 2026-04-21. Run through this list right before `git push` to innersource.*
