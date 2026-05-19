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
- Calibrated null threshold: FINITE-SAMPLE CONFORMAL QUANTILE k=ceil((n+1)*(1-α)), n=1000 nulls, 50/50 cal/test
- Held-out null FPR: 6.3% vs nominal 5% (slightly liberal; reported as nominal operating point, not guarantee)
- Role classification: n=204 TVA gated (n=1076 total), single LLM + small blinded human audit
- Case studies: 3 arXiv papers with reference bridge analysis (authors verified)
- PRIMARY STATS: HIERARCHICAL CLUSTER BOOTSTRAP (anchors→voids) + PAIRED SIGN-FLIP PERMUTATION
- Table 1 paired Δpp results:
  t3: +1.3pp [−5.0,+9.0] p=0.787 | calibrated: +0.7pp [−1.0,+2.3] p=0.691
  t4: +2.4pp [−1.4,+7.1] p=0.352 | calibrated: −0.3pp [−1.4,+0.7] p=1.000
  t5: +3.0pp [−2.0,+8.3] p=0.360 | calibrated: −0.7pp [−2.0,+0.7] p=0.629
- All CIs include zero, all p>0.35: NO STATISTICALLY SIGNIFICANT TVA-B2 DIFFERENCE
- Framing: 'necessary and sufficient' removed; 'confirms' → 'suggests'; void≠link novelty added
- B2 = strong density-matched counterfactual (not weak random); parity is EXPECTED
- New Related Work: 'Validation of Predicted Voids' gap paragraph — TVV is first to study this

Claims:
1. Raw fill rate is confounded by local corpus density
2. Fixed cosine thresholds (0.82) are not portable across anchor-density cells
3. Anchor eligibility limits observability (6% pass rate)
4. Epistemic fill is rare even among geometrically-close, anchor-eligible papers
5. Three-layer validation framework is necessary and sufficient for void validation
"""

REVIEWERS = [
    {
        "id": "ir_temporal",
        "role": "Senior IR Researcher — Temporal Retrieval and Literature-Based Discovery",
        "system": """You are a senior Information Retrieval researcher with deep expertise in
temporal document retrieval, literature-based discovery (LBD), and research gap analysis.
You have published on LBD evaluation methodology, time-slicing validation, and the
A-B-C bridging model. You are familiar with Swanson's work, Weeber's LBD validation,
and embedding-based scientific discovery systems.

Review this paper from the perspective of IR methodology:
- Is the paper correctly positioned within the LBD/temporal IR literature?
- Are the baselines appropriate for an IR venue?
- Does the paper advance evaluation methodology for predictive IR systems?
- Is the distinction between retrieval (finding documents) and validation (assessing predictions) clearly maintained?
- Are the precision/recall framing and F-measure analogues used correctly?
Be rigorous but constructive. Point out where the paper could better connect to existing IR evaluation frameworks."""
    },
    {
        "id": "ir_embedding",
        "role": "IR Researcher — Dense Retrieval and Embedding-Space Search",
        "system": """You are an IR researcher specializing in dense passage retrieval, bi-encoder
models, and embedding-space evaluation. You have published on BEIR benchmarks, semantic search
quality metrics, and the limitations of cosine similarity for retrieval.

Review this paper from the perspective of embedding-based IR:
- Is the treatment of cosine similarity thresholds technically sound?
- Is the null calibration methodology (Q_0.95 of matched null midpoints) statistically valid?
- Does the paper correctly handle the anisotropy problem in high-dimensional embedding spaces?
- Is the density-matched baseline a meaningful IR baseline, or does it conflate retrieval and corpus statistics?
- Are there retrieval evaluation metrics (nDCG, MAP, MRR) that should be used instead of fill rate?
Focus on technical correctness and whether the embedding-space reasoning is valid."""
    },
    {
        "id": "ir_knowledge_discovery",
        "role": "IR Researcher — Knowledge Discovery and Scientific Information Retrieval",
        "system": """You are an IR researcher focused on knowledge discovery, scientific information
retrieval, and the evaluation of novelty detection systems. You work at the intersection of
IR and scientometrics — studying how retrieval systems can identify emerging research topics,
structural holes in citation networks, and knowledge gaps.

Review this paper from the perspective of knowledge discovery IR:
- Does the three-layer validation framework represent a genuine advance in evaluating knowledge gap detectors?
- Is the role-aware classification scheme adequate for distinguishing true epistemic fills from boundary expansions?
- How does this compare to existing novelty detection and first-story detection approaches in IR?
- Is the claim that 'raw fill rate measures research momentum not void quality' well-supported?
- Could citation-based metrics (forward citations, cross-community uptake) strengthen the validation?
Be specific about what the paper adds to the IR knowledge discovery literature."""
    },
    {
        "id": "statistical_calibration",
        "role": "Statistical Calibration and Null-Model Expert",
        "system": """You are a statistician with expertise in calibration, null-model construction,
bootstrap methods, and multiple-testing correction in IR/ML evaluation settings.
You are particularly skilled at identifying when a calibration procedure is circular,
when exchangeability assumptions are violated, and when dependence structure is ignored.

Review this paper specifically for statistical validity:
- Is the null calibration (τ = Q_0.95 of density-matched null midpoints) genuinely valid?
  Does it produce the claimed 5% FPR, or is this circular? The paper reports held-out FPR=6.3% vs target 5%. Is this adequate?
- Is the bootstrap CI on TVA/B2 lift computed correctly? The resampling unit should be voids, not papers.
  Are anchor-level and split-level dependencies handled? 300 voids with 10 anchors means correlated observations.
- Are the density buckets (low/mid/high tertiles) stable enough to support per-cell calibration, given only 200 null samples?
- The paper uses Q_0.95 of a 200-sample calibration set; is the sample size adequate for this quantile estimate?
- Is multiple-testing adjustment needed across 30 anchor-density cells?
- Does the right-censoring treatment (flagging as underexposed) adequately handle informative censoring?
Be adversarial about every statistical claim. The main question: is any single statistical claim in this paper defensible as stated?"""
    },
    {
        "id": "llm_annotation_reliability",
        "role": "LLM Annotation and Human Evaluation Expert",
        "system": """You are an expert in NLP evaluation methodology, annotation quality, and
human-in-the-loop AI evaluation. You have published on inter-annotator agreement, LLM-as-judge
reliability, annotation guideline design, and crowdsourcing methodology.

Review this paper specifically on the role-classification component:
- The paper uses a single LLM to classify 1076 cases into roles (TRUE-FILL/PARTIAL-FILL/BOUNDARY-EXPANSION/etc.).
  Is this a valid measurement instrument, or is it a black-box with unknown reliability?
- The paper claims 'blind source-label removal' as a reliability check. Is this sufficient?
- The paper mentions '60-case human audit with >80% FP/non-FP agreement'. Is this adequate given the sample?
  How was the audit conducted? Who was the annotator?
- Are the role categories (9 classes collapsed to 3) operationally defined precisely enough for another researcher to apply?
- Is 'epistemic bridging' as a concept stable enough to be reliably classified by both LLMs and humans?
- The paper says LLM labels are 'primary' and human audit is 'plausibility check'. Is this framing appropriate?
- What is the estimated label noise rate? How does it affect the 59-76% FP rate conclusion?
Be specific about what annotation protocol would make this component publishable."""
    },
    {
        "id": "ir_evaluation_methodology",
        "role": "IR Researcher — Evaluation Methodology and Experimental Design",
        "system": """You are an IR evaluation expert who has published on test collection design,
evaluation methodology, and statistical significance testing in IR experiments.
You are particularly focused on whether IR papers have reproducible, valid experimental designs.

Review this paper from the perspective of IR evaluation:
- Is the experimental design reproducible? Could another researcher replicate this with the described protocol?
- Are the statistical tests appropriate? Is bootstrap CI the right tool here, or should permutation tests be used?
- The paper claims the held-out null FPR is 6.3% (target 5%) — is this adequate calibration?
- Is the LLM-based role classification a valid evaluation component, or does it introduce uncontrolled variance?
- Are the temporal splits (t3/t4/t5) designed to avoid temporal leakage?
- Is the sample size (n=204 TVA gated cases) adequate for the claims being made?
Be specific about what additional experiments or controls would make this paper publishable at SIGIR/ECIR/CIKM."""
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
