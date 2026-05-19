"""
scripts/temporal_validation/select_case_studies.py

Select 3 representative case studies from role classification results.

Target cases:
  Case 1: PARTIAL_FILL (best available — highest confidence)
  Case 2: BOUNDARY_EXPANSION / INCREMENTAL_EXTENSION (TVA, not FP)
  Case 3: FALSE_POSITIVE / DENSIFICATION (geometrically close but epistemically empty)

For each, reports:
  - Anchor + void (A/B paper titles)
  - Future paper (title, year, sim_to_midpoint, sim_to_anchor)
  - Role label + LLM reason
  - topological_event_type
  - problem_conclusion_alignment, claim_evidence_strength, overclaiming_risk
  - arXiv ID (for manual citation lookup)

Usage:
    python scripts/temporal_validation/select_case_studies.py --split t5
    python scripts/temporal_validation/select_case_studies.py --splits t3 t4 t5
"""

import argparse
import json
from pathlib import Path

OUTPUT_DIR = Path("data/processed/tvv/rolling")

ROLE_WEIGHTS = {
    "TRUE_FILL": 1.0, "PARTIAL_FILL": 0.7, "SUPPORT_EVIDENCE": 0.5,
    "BENCHMARK_OR_MEASUREMENT": 0.4, "SURVEY_OR_NAMING": 0.3,
    "INCREMENTAL_EXTENSION": 0.2, "FALSE_POSITIVE": 0.0,
}

TARGET_SOURCES = {"tva", "baseline", "b2_density"}  # exclude near_miss


def load_results(split_name: str) -> list[dict]:
    path = OUTPUT_DIR / split_name / "role_classification_v2.json"
    if not path.exists():
        return []
    data = json.load(open(path))
    return [r for r in data["results"]
            if r["case"].get("source") in TARGET_SOURCES]


def score(r: dict) -> float:
    return ROLE_WEIGHTS.get(r["classification"].get("role", ""), 0)


def pick_cases(results: list[dict]) -> dict:
    """Pick best 3 cases by type."""
    partial_fills = [r for r in results
                     if r["classification"].get("role") in {"TRUE_FILL", "PARTIAL_FILL"}]
    boundary = [r for r in results
                if r["classification"].get("role") in {"INCREMENTAL_EXTENSION", "SUPPORT_EVIDENCE",
                                                        "SURVEY_OR_NAMING"}
                and r["classification"].get("topological_event_type") == "BOUNDARY_EXPANSION"]
    fp_dense = [r for r in results
                if r["classification"].get("role") == "FALSE_POSITIVE"
                and r["classification"].get("topological_event_type") in {"DENSIFICATION", "RHETORICAL_BRIDGE"}]

    cases = {}

    # Case 1: PARTIAL_FILL — sort by confidence
    if partial_fills:
        partial_fills.sort(key=lambda r: r["classification"].get("confidence", 0), reverse=True)
        cases["case1_partial_fill"] = partial_fills[0]
    else:
        # fallback: highest-score case overall
        best = max(results, key=score)
        cases["case1_partial_fill"] = best

    # Case 2: BOUNDARY_EXPANSION — pick one from TVA source if possible
    tva_boundary = [r for r in boundary if r["case"].get("source") == "tva"]
    if tva_boundary:
        # highest sim_to_midpoint
        tva_boundary.sort(key=lambda r: r["case"].get("filler", {}).get("sim_to_midpoint", 0), reverse=True)
        cases["case2_boundary"] = tva_boundary[0]
    elif boundary:
        cases["case2_boundary"] = boundary[0]

    # Case 3: FP / DENSIFICATION — pick one with highest sim_to_midpoint (most "convincing" FP)
    if fp_dense:
        fp_dense.sort(key=lambda r: r["case"].get("filler", {}).get("sim_to_midpoint", 0), reverse=True)
        cases["case3_fp"] = fp_dense[0]
    else:
        # fallback: any FP
        fps = [r for r in results if r["classification"].get("role") == "FALSE_POSITIVE"]
        if fps:
            fps.sort(key=lambda r: r["case"].get("filler", {}).get("sim_to_midpoint", 0), reverse=True)
            cases["case3_fp"] = fps[0]

    return cases


def format_case(label: str, r: dict) -> str:
    case = r["case"]
    clf = r["classification"]
    src_a = case.get("source_a", {})
    src_b = case.get("source_b", {})
    filler = case.get("filler", {})

    lines = [
        f"{'='*70}",
        f"{label}  |  source={case.get('source')}  anchor={case.get('anchor_id')}",
        f"{'='*70}",
        f"ANCHOR: {case.get('anchor', '')}",
        f"",
        f"SOURCE A ({src_a.get('year', '?')}): {src_a.get('title', 'N/A')[:80]}",
        f"  arXiv: {src_a.get('id', 'N/A')}",
        f"SOURCE B ({src_b.get('year', '?')}): {src_b.get('title', 'N/A')[:80]}",
        f"  arXiv: {src_b.get('id', 'N/A')}",
        f"",
        f"FUTURE PAPER ({filler.get('year', '?')}): {filler.get('title', 'N/A')[:80]}",
        f"  arXiv: {filler.get('id', 'N/A')}",
        f"  sim_to_midpoint: {filler.get('sim_to_midpoint', 0):.4f}",
        f"  sim_to_anchor:   {filler.get('sim_to_anchor', 0):.4f}  (legacy τ=0.82)",
        f"",
        f"ROLE: {clf.get('role', '?')}  (confidence={clf.get('confidence', 0):.2f})",
        f"TOPOLOGICAL EVENT: {clf.get('topological_event_type', '?')}",
        f"",
        f"Epistemic scores:",
        f"  anchor_relevance:            {clf.get('anchor_relevance', '?')}  /3",
        f"  void_relevance:              {clf.get('void_relevance', '?')}  /3",
        f"  novelty_relative_to_sources: {clf.get('novelty_relative_to_sources', '?')}  /3",
        f"  evidence_strength:           {clf.get('evidence_strength', '?')}  /3",
        f"  problem_conclusion_align:    {clf.get('problem_conclusion_alignment', '?')}  /2",
        f"  claim_evidence_strength:     {clf.get('claim_evidence_strength', '?')}  /2",
        f"  overclaiming_risk:           {clf.get('overclaiming_risk', '?')}",
        f"",
        f"REASON: {clf.get('reason', 'N/A')}",
        f"",
        f"[TODO: look up citation count for arXiv {filler.get('id', 'N/A')}]",
        f"[TODO: check if filler cites A-side / B-side / both]",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--splits", nargs="+", default=["t5"])
    args = parser.parse_args()

    all_results = []
    for s in args.splits:
        r = load_results(s)
        if r:
            all_results.extend(r)
            print(f"Loaded {len(r)} results from {s}")

    if not all_results:
        print("No results found.")
        return

    cases = pick_cases(all_results)

    if not cases:
        print("Could not find sufficient cases.")
        return

    print(f"\nSELECTED CASE STUDIES  (from {len(all_results)} total)\n")
    for label, r in cases.items():
        print(format_case(label.upper(), r))
        print()

    # Save for paper notes
    out = {label: {"case": r["case"], "classification": r["classification"]}
           for label, r in cases.items()}
    out_path = OUTPUT_DIR / "case_studies.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved → {out_path}")
    print("\nNEXT STEPS:")
    print("  1. Look up each arXiv ID on Semantic Scholar for citation count + reference list")
    print("  2. Check if filler paper cites papers from A-side, B-side, or both")
    print("  3. Note citation trajectory (immediate burst / slow growth / flat)")


if __name__ == "__main__":
    main()
