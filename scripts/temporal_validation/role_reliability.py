"""
scripts/temporal_validation/role_reliability.py

Task 9: LLM annotation reliability table for Paper 2.

Three checks:
  1. Self-consistency: re-run same LLM on 100 stratified cases → Cohen's κ
  2. Cross-LLM:        same cases with a second model → Cohen's κ
  3. (Optional) human audit already done in paper (80%+ agreement cited in §3)

Stratified sample: balanced across source groups (TVA/B1/B2/near_miss)
and LLM label (fill/non-fill).

Usage:
    python scripts/temporal_validation/role_reliability.py --split t5 --n 100
    python scripts/temporal_validation/role_reliability.py --split t5 --n 100 --second-model gpt-4o
"""

import argparse
import json
import random
from collections import Counter
from pathlib import Path

import numpy as np
from loguru import logger

OUTPUT_DIR = Path("data/processed/tvv/rolling")


def stratified_sample(cases: list, n: int, seed: int = 42) -> list:
    """Sample n cases stratified by source × collapsed_label."""
    rng = random.Random(seed)
    groups = {}
    for r in cases:
        src = r["case"].get("source", "?")
        role = r["classification"].get("role", "UNCLEAR")
        collapsed = "fill" if role in {"TRUE_FILL", "PARTIAL_FILL"} else "non_fill"
        key = f"{src}_{collapsed}"
        groups.setdefault(key, []).append(r)

    # Round-robin from groups until we have n
    sampled = []
    keys = sorted(groups.keys())
    idx = {k: 0 for k in keys}
    while len(sampled) < n:
        added = False
        for k in keys:
            if idx[k] < len(groups[k]) and len(sampled) < n:
                sampled.append(groups[k][idx[k]])
                idx[k] += 1
                added = True
        if not added:
            break  # exhausted all groups

    rng.shuffle(sampled)
    return sampled[:n]


def classify_case(case: dict, llm_client, model: str) -> dict:
    from agents.json_parser import robust_json_parse
    from configs.settings import settings

    src_a = case.get("source_a", {})
    src_b = case.get("source_b", {})
    filler = case.get("filler", {})

    prompt = f"""You are classifying the epistemic role of a candidate future paper relative to a proposed research void.
Do not judge whether the paper is generally good. Judge only what it does with respect to the void.

Anchor: {case.get('anchor', '')}
Source A ({src_a.get('year','?')}): {src_a.get('title','')[:100]}
Abstract A: {(src_a.get('abstract','') or '')[:300]}
Source B ({src_b.get('year','?')}): {src_b.get('title','')[:100]}
Abstract B: {(src_b.get('abstract','') or '')[:300]}
Candidate future paper ({filler.get('year','?')}): {filler.get('title','')[:100]}
Abstract: {(filler.get('abstract','') or '')[:300]}

Classify into: TRUE_FILL / PARTIAL_FILL / INCREMENTAL_EXTENSION / SUPPORT_EVIDENCE / BENCHMARK_OR_MEASUREMENT / SURVEY_OR_NAMING / REFUTATION_OR_COLLAPSE / FALSE_POSITIVE / UNCLEAR

Return strict JSON only:
{{"role": "ONE_OF_THE_ROLES_ABOVE", "confidence": 0.0, "reason": "brief"}}"""

    try:
        raw = llm_client.chat(
            model=model,
            system_prompt="You are classifying epistemic roles. Return only valid JSON.",
            user_prompt=prompt,
            temperature=0.1,
        )
        result = robust_json_parse(raw)
        if not result or "role" not in result:
            return {"role": "UNCLEAR", "confidence": 0, "reason": "parse_failed"}
        result["role"] = result["role"].upper().replace(" ", "_")
        return result
    except Exception as e:
        return {"role": "UNCLEAR", "confidence": 0, "reason": str(e)}


def collapse_role(role: str) -> str:
    if role in {"TRUE_FILL", "PARTIAL_FILL"}:
        return "fill"
    return "non_fill"


def compute_kappa(labels1: list, labels2: list) -> tuple[float, float, float]:
    """Returns (kappa_binary, kappa_3class, pct_agreement_binary)."""
    from sklearn.metrics import cohen_kappa_score

    b1 = [collapse_role(r) for r in labels1]
    b2 = [collapse_role(r) for r in labels2]
    pct = sum(1 for a, b in zip(b1, b2) if a == b) / len(b1)

    try:
        k_binary = cohen_kappa_score(b1, b2)
    except Exception:
        k_binary = float("nan")

    # 3-class
    def c3(r):
        if r in {"TRUE_FILL", "PARTIAL_FILL"}: return "void_res"
        if r in {"INCREMENTAL_EXTENSION", "SUPPORT_EVIDENCE", "BENCHMARK_OR_MEASUREMENT", "SURVEY_OR_NAMING"}: return "boundary"
        return "fp_unclear"

    c1 = [c3(r) for r in labels1]
    c2 = [c3(r) for r in labels2]
    try:
        k_3class = cohen_kappa_score(c1, c2)
    except Exception:
        k_3class = float("nan")

    return k_binary, k_3class, pct


def run(split_name: str, n_sample: int, second_model: str | None):
    from agents.llm_client import LLMClient
    from configs.settings import settings

    data = json.load(open(OUTPUT_DIR / split_name / "role_classification_v2.json"))
    all_cases = data["results"]
    sample = stratified_sample(all_cases, n_sample)
    logger.info(f"Sampled {len(sample)} cases (stratified)")
    src_dist = Counter(r["case"].get("source", "?") for r in sample)
    role_dist = Counter(collapse_role(r["classification"]["role"]) for r in sample)
    logger.info(f"  Source dist: {dict(src_dist)}")
    logger.info(f"  Label dist (binary): {dict(role_dist)}")

    llm = LLMClient()
    primary_model = settings.debate_deep_thinker_model

    # Original labels from v2 file
    labels_orig = [r["classification"]["role"] for r in sample]
    cases_only = [r["case"] for r in sample]

    # --- Self-consistency replay ---
    logger.info(f"\nReplay 1: self-consistency ({primary_model})...")
    labels_replay = []
    for i, case in enumerate(cases_only):
        result = classify_case(case, llm, primary_model)
        labels_replay.append(result["role"])
        if (i + 1) % 20 == 0:
            logger.info(f"  {i+1}/{len(cases_only)}")

    k_bin1, k_3c1, pct1 = compute_kappa(labels_orig, labels_replay)
    logger.info(f"  Self-consistency κ (binary)={k_bin1:.3f}  κ (3-class)={k_3c1:.3f}  agreement={pct1:.1%}")

    # --- Cross-LLM (if second model provided) ---
    labels_cross = None
    k_bin2 = k_3c2 = pct2 = None
    if second_model:
        logger.info(f"\nReplay 2: cross-LLM ({second_model})...")
        labels_cross = []
        for i, case in enumerate(cases_only):
            result = classify_case(case, llm, second_model)
            labels_cross.append(result["role"])
            if (i + 1) % 20 == 0:
                logger.info(f"  {i+1}/{len(cases_only)}")
        k_bin2, k_3c2, pct2 = compute_kappa(labels_orig, labels_cross)
        logger.info(f"  Cross-LLM κ (binary)={k_bin2:.3f}  κ (3-class)={k_3c2:.3f}  agreement={pct2:.1%}")

    # Print summary table
    print(f"\n{'='*60}")
    print(f"ROLE ANNOTATION RELIABILITY (n={len(sample)}, split={split_name})")
    print(f"{'='*60}")
    print(f"{'Comparison':<25} {'n':>4}  {'κ binary':>9}  {'κ 3-class':>10}  {'Agree%':>7}")
    print("-" * 60)
    print(f"{'Self-consistency':<25} {len(sample):>4}  {k_bin1:>9.3f}  {k_3c1:>10.3f}  {pct1:>6.1%}")
    if k_bin2 is not None:
        print(f"{'Cross-LLM':<25} {len(sample):>4}  {k_bin2:>9.3f}  {k_3c2:>10.3f}  {pct2:>6.1%}")
    print(f"\n  Interpretation:")
    print(f"    κ ≥ 0.8 = substantial agreement")
    print(f"    κ 0.6–0.8 = moderate-substantial")
    print(f"    κ 0.4–0.6 = moderate")
    print(f"    κ < 0.4 = weak (concern)")

    result = {
        "split": split_name,
        "n_sample": len(sample),
        "primary_model": primary_model,
        "self_consistency": {
            "kappa_binary": round(k_bin1, 4),
            "kappa_3class": round(k_3c1, 4),
            "agreement_pct": round(pct1, 4),
        },
    }
    if k_bin2 is not None:
        result["cross_llm"] = {
            "model": second_model,
            "kappa_binary": round(k_bin2, 4),
            "kappa_3class": round(k_3c2, 4),
            "agreement_pct": round(pct2, 4),
        }

    out_path = OUTPUT_DIR / split_name / "role_reliability.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    logger.info(f"Saved → {out_path}")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="t5")
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--second-model", default=None, help="Cross-LLM model name")
    args = parser.parse_args()
    run(args.split, args.n, args.second_model)


if __name__ == "__main__":
    main()
