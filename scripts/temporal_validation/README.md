# TVV — Topological Void Validation

Second paper experiments: objective validation of TVA using temporal holdout.

## Core Question

Do the voids TVA finds in a corpus at time `t < T` correspond to real
knowledge gaps that get filled in `t = T ~ T+4 years`?

## Data

- **Linux corpus**: kernel source + commit history (already ingested)
- **arXiv**: `data/raw/arxiv/arxiv-metadata-oai-snapshot.json` (snapshot up to 2023-09)

## Time Split

| Split | Range | Purpose |
|---|---|---|
| Training corpus | `t < 2019` | Build vector DB, find voids |
| Validation window | `t = 2019–2023` | Check if voids got filled |

## Experiment Steps

1. Rebuild vector DB using only `t < 2019` documents
2. Run TVA, find top-N voids
3. For each void, check if any `t = 2019–2023` document lands nearby
4. Compute precision / recall
5. Side experiment: validate `f(coordinate, intent) → meaning`

**No LLM required. No Debate Panel. Pure geometry + timestamps.**

## Scripts (TODO)

- `build_temporal_corpus.py` — rebuild DB with date filter
- `run_temporal_void_search.py` — find voids in t<2019 corpus
- `validate_void_fill_rate.py` — check fill rate in validation window
- `arxiv_temporal_split.py` — extract arXiv papers by year

## Why This Matters

Addresses the main weaknesses of Paper 1:
- N=8 human evaluation → replaced by objective git/arXiv ground truth
- k circular argument → k can be calibrated against fill rate
- No baseline comparison → fill rate IS the baseline
- "TVA finds real voids" claim → now empirically testable
