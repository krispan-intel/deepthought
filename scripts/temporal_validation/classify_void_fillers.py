"""
scripts/temporal_validation/classify_void_fillers.py

Epistemic role classification for void fillers.

Reads pre-built filled cases JSONL (output of run_rolling_validation.py).
Does NOT re-run fill detection or baseline generation.
Blind classification: source label (tva/baseline) is not shown to LLM.

Roles:
  TRUE_FILL, PARTIAL_FILL, INCREMENTAL_EXTENSION, SUPPORT_EVIDENCE,
  BENCHMARK_OR_MEASUREMENT, SURVEY_OR_NAMING, REFUTATION_OR_COLLAPSE,
  FALSE_POSITIVE, UNCLEAR

Usage:
    # Classify a rolling split's filled cases
    python scripts/temporal_validation/classify_void_fillers.py \\
      --cases-file data/processed/tvv/rolling/t5/filled_cases_raw.jsonl \\
      --output data/processed/tvv/rolling/t5/role_classification_raw.json

    # Quick test
    python scripts/temporal_validation/classify_void_fillers.py \\
      --cases-file data/processed/tvv/rolling/t5/filled_cases_raw.jsonl \\
      --max-cases 10
"""

import argparse
import json
from pathlib import Path

from loguru import logger

ROLE_WEIGHTS = {
    "TRUE_FILL": 1.0,
    "PARTIAL_FILL": 0.7,
    "SUPPORT_EVIDENCE": 0.5,
    "BENCHMARK_OR_MEASUREMENT": 0.4,
    "SURVEY_OR_NAMING": 0.3,
    "INCREMENTAL_EXTENSION": 0.2,
    "REFUTATION_OR_COLLAPSE": None,  # separate event
    "FALSE_POSITIVE": 0.0,
    "UNCLEAR": None,  # exclude from scoring
}

CLASSIFICATION_PROMPT = """You are classifying the epistemic role of a candidate future paper relative to a proposed research void.

Do not judge whether the paper is generally good. Judge only what the candidate paper does with respect to the void implied by the anchor and the two source papers.

Anchor (the research direction defining this void):
{anchor}

Source paper A (year: {year_a}):
Title: {title_a}
Abstract: {abstract_a}

Source paper B (year: {year_b}):
Title: {title_b}
Abstract: {abstract_b}

Candidate future paper (year: {year_f}):
Title: {title_f}
Abstract: {abstract_f}

Classify the candidate paper into exactly one role:

- TRUE_FILL: proposes a new method, theory, mechanism, or synthesis that substantively fills the gap between the source papers under the anchor.
- PARTIAL_FILL: addresses part of the gap but does not fully resolve it.
- INCREMENTAL_EXTENSION: mainly extends one source direction without bridging the gap.
- SUPPORT_EVIDENCE: provides empirical evidence relevant to the gap but does not propose a new solution.
- BENCHMARK_OR_MEASUREMENT: introduces dataset, benchmark, metric, or evaluation method relevant to the gap.
- SURVEY_OR_NAMING: names, reviews, or frames the gap without filling it.
- REFUTATION_OR_COLLAPSE: provides evidence or argument that undermines the gap or makes the proposed direction invalid.
- FALSE_POSITIVE: semantically close but not actually relevant to the void.
- UNCLEAR: abstract is insufficient to determine.

Return strict JSON only (no markdown, no explanation outside JSON):
{{
  "role": "ONE_OF_THE_ROLES_ABOVE",
  "confidence": 0.0,
  "anchor_relevance": 0,
  "void_relevance": 0,
  "novelty_relative_to_sources": 0,
  "evidence_strength": 0,
  "problem_conclusion_alignment": 0,
  "claim_evidence_strength": 0,
  "overclaiming_risk": "LOW",
  "topological_event_type": "VOID_FILL",
  "reason": "one concise paragraph",
  "needs_full_text": false
}}

anchor_relevance, void_relevance, novelty_relative_to_sources, evidence_strength are integers 0-3.
problem_conclusion_alignment: does the conclusion match the problem scope? (0=mismatch/overclaim, 1=partial, 2=well-aligned)
claim_evidence_strength: how well does the abstract evidence support the claimed contribution? (0=weak/speculative, 1=moderate, 2=strong)
overclaiming_risk: does the paper claim more than its abstract evidence supports? (LOW / MEDIUM / HIGH)
topological_event_type: what kind of topological event does this paper induce relative to the void?
  VOID_FILL — first paper to occupy a previously vacant bridge region; substantively bridges the two source directions
  BOUNDARY_EXPANSION — extends one or both source directions but does not bridge the gap
  DENSIFICATION — falls in already-occupied region; no new structural contribution
  RHETORICAL_BRIDGE — geometrically close but no epistemic work; overclaims bridging
  COLLAPSE — undermines or invalidates the void itself"""


def load_cases(path: Path, max_cases: int = None) -> list[dict]:
    cases = []
    with open(path) as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))
    if max_cases:
        cases = cases[:max_cases]
    return cases


def classify_case(case: dict, llm_client) -> dict:
    from configs.settings import settings
    from agents.json_parser import robust_json_parse

    src_a = case.get("source_a", {})
    src_b = case.get("source_b", {})
    filler = case.get("filler", {})

    prompt = CLASSIFICATION_PROMPT.format(
        anchor=case.get("anchor", ""),
        year_a=src_a.get("year", "?"),
        title_a=(src_a.get("title", "") or "")[:200],
        abstract_a=(src_a.get("abstract", "") or "")[:500],
        year_b=src_b.get("year", "?"),
        title_b=(src_b.get("title", "") or "")[:200],
        abstract_b=(src_b.get("abstract", "") or "")[:500],
        year_f=filler.get("year", "?"),
        title_f=(filler.get("title", "") or "")[:200],
        abstract_f=(filler.get("abstract", "") or "")[:500],
    )

    try:
        response = llm_client.chat(
            model=settings.debate_deep_thinker_model,
            system_prompt="You are a research assistant classifying epistemic roles. Return only valid JSON.",
            user_prompt=prompt,
            temperature=0.1,
        )
        result = robust_json_parse(response)
        if not result or "role" not in result:
            return {"role": "UNCLEAR", "confidence": 0, "reason": "parse_failed", "raw": response[:200]}
        result["role"] = result["role"].upper().replace(" ", "_")
        valid_roles = set(ROLE_WEIGHTS.keys()) | {"REFUTATION_OR_COLLAPSE", "UNCLEAR"}
        if result["role"] not in valid_roles:
            result["role"] = "UNCLEAR"
        return result
    except Exception as e:
        return {"role": "UNCLEAR", "confidence": 0, "reason": str(e)}


def summarize(results: list[dict]) -> dict:
    from collections import Counter, defaultdict

    by_source = defaultdict(list)
    for r in results:
        by_source[r["case"]["source"]].append(r)

    summary = {}
    for source, cases in by_source.items():
        roles = Counter(c["classification"]["role"] for c in cases)
        scores = [
            ROLE_WEIGHTS.get(c["classification"]["role"], 0) or 0
            for c in cases
            if c["classification"]["role"] not in {"UNCLEAR", "REFUTATION_OR_COLLAPSE"}
        ]
        non_fp = sum(1 for c in cases if c["classification"]["role"] != "FALSE_POSITIVE"
                     and c["classification"]["role"] != "UNCLEAR")
        summary[source] = {
            "n": len(cases),
            "roles": dict(roles),
            "false_positive_rate": roles.get("FALSE_POSITIVE", 0) / len(cases) if cases else 0,
            "non_fp_rate": non_fp / len(cases) if cases else 0,
            "role_aware_score_mean": sum(scores) / len(scores) if scores else 0,
        }

    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases-file", required=True, help="JSONL of filled cases to classify")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")
    parser.add_argument("--max-cases", type=int, default=None)
    args = parser.parse_args()

    cases_path = Path(args.cases_file)
    if not cases_path.exists():
        logger.error(f"Cases file not found: {cases_path}")
        return

    output_path = Path(args.output) if args.output else cases_path.parent / (cases_path.stem + "_classified.json")

    cases = load_cases(cases_path, args.max_cases)
    logger.info(f"Loaded {len(cases)} cases from {cases_path}")

    tva_n = sum(1 for c in cases if c.get("source") == "tva")
    base_n = sum(1 for c in cases if c.get("source") == "baseline")
    logger.info(f"  TVA: {tva_n}  Baseline: {base_n}")

    from agents.llm_client import LLMClient
    llm = LLMClient()

    results = []
    for i, case in enumerate(cases):
        logger.info(f"[{i+1}/{len(cases)}] {case['case_id']} ({case.get('source', '?')})")
        classification = classify_case(case, llm)
        results.append({"case": case, "classification": classification})

    summary = summarize(results)

    print(f"\n{'='*55}")
    print("EPISTEMIC ROLE DISTRIBUTION")
    print(f"{'Role':<35} {'TVA':>6} {'Base':>6}")
    print("-" * 55)
    from collections import Counter
    tva_roles = Counter(r["classification"]["role"] for r in results if r["case"].get("source") == "tva")
    base_roles = Counter(r["classification"]["role"] for r in results if r["case"].get("source") == "baseline")
    all_roles = sorted(set(list(tva_roles.keys()) + list(base_roles.keys())))
    for role in all_roles:
        print(f"{role:<35} {tva_roles.get(role,0):>6} {base_roles.get(role,0):>6}")

    print(f"\n{'='*55}")
    print("ROLE-AWARE FILL SCORE")
    for source, s in summary.items():
        print(f"  {source:<12}: mean={s['role_aware_score_mean']:.3f}  n={s['n']}  fp_rate={s['false_positive_rate']:.0%}")

    output = {
        "cases_file": str(cases_path),
        "n_total": len(results),
        "summary": summary,
        "results": results,
    }
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    logger.info(f"Saved → {output_path}")


if __name__ == "__main__":
    main()
