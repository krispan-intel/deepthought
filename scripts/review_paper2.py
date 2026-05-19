"""
scripts/review_paper2.py

Run a 4-specialist debate panel review of Paper 2 (TVV).
Reviewers: IR specialist, scientometrics, embedding/ML, methods critic.
Output: per-reviewer verdict + chairman synthesis.

Usage:
    python scripts/review_paper2.py
    python scripts/review_paper2.py --output notes/paper2_review.json
"""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from loguru import logger
from agents.llm_client import LLMClient
from agents.json_parser import robust_json_parse
from configs.settings import settings

PAPER2_ABSTRACT = """
Title: Topological Void Validation: Density-Controlled and Role-Aware Evaluation of Predicted Research Voids

Abstract:
Topological Void Analysis (TVA) identifies candidate research voids in scientific knowledge spaces as
geometric gaps between anchor-conditioned paper clusters. A natural validation question is whether
future papers fill these predicted voids. We show that raw fill rate fails as a validation target
for three compounding reasons: (1) density confound — a hot-zone baseline outperforms TVA on raw
fill (36% vs 28%), but this reverses under a density-matched baseline (25%; TVA/B2 lift 1.12x,
CI [0.85, 1.48], not significant); (2) observability limits — only 5-7% of future papers are
anchor-eligible, so unfilled voids should be treated as right-censored; (3) threshold non-portability
— a fixed threshold 0.82 has 35.7% average null FPR (range 1-99%), and under null-calibrated
thresholds fill rates collapse from ~27% to ~0.7%. Role-aware epistemic classification shows that
even anchor-eligible geometric fills are 59-76% false positives, with most non-false cases
representing boundary expansion rather than epistemic closure. We propose a three-layer validation
framework: calibrated geometric closure, anchor eligibility, and epistemic role.

Key experimental results:
- Rolling temporal splits t3/t4/t5 (arXiv CS, 29k-51k train, 101k-193k val papers)
- 10 anchors × 30 voids = 300 TVA candidates per split
- B1 (hot-zone) baseline and B2 (density-matched) baseline
- Calibrated null threshold: τ_fill(q,ρ,t) = Q_0.95 of density-matched null midpoint occupancy
- Role classification: TRUE-FILL/PARTIAL-FILL/BOUNDARY-EXPANSION/DENSIFICATION/FALSE-POSITIVE
- Case studies: 3 arXiv papers with reference bridge analysis and citation counts

Claims:
1. Raw fill rate is confounded by local corpus density
2. Fixed cosine thresholds (0.82) are not portable across anchor-density cells
3. Anchor eligibility limits observability (6% pass rate)
4. Epistemic fill is rare even among geometrically-close, anchor-eligible papers
5. Three-layer validation framework is necessary and sufficient for void validation
"""

REVIEWERS = [
    {
        "id": "ir_specialist",
        "role": "Information Retrieval Specialist",
        "system": """You are a senior IR researcher with expertise in temporal information retrieval,
literature-based discovery (LBD), and embedding-based search. You review papers critically for
correctness of IR framing, validity of baselines, and whether the paper advances IR methodology.
Be rigorous. Flag any confusion between retrieval and validation, weak baselines, or overclaiming."""
    },
    {
        "id": "scientometrics",
        "role": "Scientometrics and Research Evaluation Expert",
        "system": """You are a scientometrics researcher specializing in knowledge gap analysis,
citation dynamics, and research front detection. You evaluate whether the paper's temporal
validation methodology is sound, whether right-censoring is handled correctly, and whether
the statistical claims are defensible given sample sizes."""
    },
    {
        "id": "ml_embedding",
        "role": "Machine Learning / Embedding Space Researcher",
        "system": """You are an ML researcher specializing in high-dimensional embedding spaces,
anisotropy, and dense retrieval. You review the paper's treatment of cosine similarity thresholds,
the null calibration methodology, and whether the density-matching approach is valid.
Check for technical errors in the embedding-space reasoning."""
    },
    {
        "id": "methods_critic",
        "role": "Research Methods and Validity Critic",
        "system": """You are a methodologist who reviews papers for threats to validity, statistical
rigor, and reproducibility. Scrutinize: sample sizes (n=98 TVA gated cases across 3 splits),
LLM role classification reliability, bootstrap CI width, and whether the calibration methodology
could be circular. Be adversarial but constructive."""
    },
]

REVIEW_PROMPT = """
You are reviewing the following paper for a top-tier IR / scientometrics venue.

{paper}

Your role: {role}

Provide a structured review. Return strict JSON:
{{
  "verdict": "ACCEPT|MAJOR_REVISION|MINOR_REVISION|REJECT",
  "score": 1,
  "summary": "2-3 sentence overall assessment",
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "weaknesses": ["weakness 1", "weakness 2", "weakness 3"],
  "fatal_flaw": "describe if verdict is REJECT, else empty string",
  "questions_for_authors": ["question 1", "question 2"],
  "suggested_fix": "most important single fix"
}}

Score: 1=strong reject, 2=reject, 3=weak reject, 4=borderline, 5=weak accept, 6=accept, 7=strong accept.
Be rigorous. If the paper's sample sizes or statistical claims are weak, say so explicitly.
"""


def review_one(reviewer: dict, paper: str, llm: LLMClient) -> dict:
    prompt = REVIEW_PROMPT.format(paper=paper, role=reviewer["role"])
    raw = llm.chat(
        model=settings.debate_deep_thinker_model,
        system_prompt=reviewer["system"],
        user_prompt=prompt,
        temperature=0.3,
    )
    result = robust_json_parse(raw)
    if not result:
        result = {"verdict": "MAJOR_REVISION", "score": 4,
                  "summary": "Parse failed", "raw": raw[:500]}
    result["reviewer"] = reviewer["id"]
    result["role"] = reviewer["role"]
    return result


def chairman_synthesis(reviews: list[dict], llm: LLMClient) -> dict:
    reviews_text = json.dumps(reviews, indent=2)
    prompt = f"""You are the Area Chair synthesizing 4 specialist reviews of a paper.

Reviews:
{reviews_text}

Based on the reviews, provide the final editorial decision. Return strict JSON:
{{
  "final_verdict": "ACCEPT|MAJOR_REVISION|MINOR_REVISION|REJECT",
  "average_score": 0.0,
  "consensus": "brief description of reviewer agreement/disagreement",
  "top_strengths": ["strength 1", "strength 2"],
  "top_concerns": ["concern 1", "concern 2", "concern 3"],
  "required_revisions": ["revision 1", "revision 2"],
  "optional_improvements": ["improvement 1"],
  "recommendation_to_authors": "2-3 sentence summary of what to do next"
}}"""

    raw = llm.chat(
        model=settings.debate_judge_model,
        system_prompt="You are an experienced area chair making an editorial decision. Be fair but rigorous.",
        user_prompt=prompt,
        temperature=0.2,
    )
    result = robust_json_parse(raw)
    if not result:
        result = {"final_verdict": "MAJOR_REVISION", "raw": raw[:500]}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="notes/paper2_panel_review.json")
    args = parser.parse_args()

    llm = LLMClient()
    logger.info("Running 4-reviewer debate panel on Paper 2 (TVV)...")

    # Parallel specialist reviews
    reviews = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(review_one, r, PAPER2_ABSTRACT, llm): r["id"]
            for r in REVIEWERS
        }
        for fut in as_completed(futures):
            rid = futures[fut]
            try:
                result = fut.result()
                reviews.append(result)
                logger.info(f"  [{rid}] verdict={result.get('verdict')} score={result.get('score')}")
            except Exception as e:
                logger.error(f"  [{rid}] failed: {e}")
                reviews.append({"reviewer": rid, "verdict": "ERROR", "error": str(e)})

    # Chairman synthesis
    logger.info("Running chairman synthesis...")
    chair = chairman_synthesis(reviews, llm)
    logger.info(f"  Final verdict: {chair.get('final_verdict')}")

    output = {
        "paper": "TVV Paper 2",
        "model_deep_thinker": settings.debate_deep_thinker_model,
        "model_judge": settings.debate_judge_model,
        "reviews": reviews,
        "chairman": chair,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    logger.info(f"Saved → {out_path}")

    # Print summary
    print(f"\n{'='*60}")
    print("PAPER 2 DEBATE PANEL REVIEW")
    print(f"{'='*60}")
    for r in sorted(reviews, key=lambda x: x.get("score", 0), reverse=True):
        print(f"\n[{r['reviewer']}] {r.get('verdict')} (score={r.get('score')})")
        print(f"  {r.get('summary', '')}")
        if r.get("fatal_flaw"):
            print(f"  FATAL: {r['fatal_flaw']}")
        for i, w in enumerate(r.get("weaknesses", [])[:2], 1):
            print(f"  W{i}: {w}")

    print(f"\n{'='*60}")
    print(f"CHAIRMAN: {chair.get('final_verdict')}")
    print(f"Consensus: {chair.get('consensus', '')}")
    for c in chair.get("top_concerns", []):
        print(f"  - {c}")
    print(f"\nTo authors: {chair.get('recommendation_to_authors', '')}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
