"""
scripts/temporal_validation/arxiv_temporal_split.py

Split arXiv metadata snapshot by year and category.
Outputs two JSONL files:
  - data/processed/tvv/arxiv_train.jsonl   (t < 2019, relevant categories)
  - data/processed/tvv/arxiv_val.jsonl     (t >= 2019, relevant categories)

Usage:
    python scripts/temporal_validation/arxiv_temporal_split.py
    python scripts/temporal_validation/arxiv_temporal_split.py --categories cs.OS cs.AR cs.PL
    python scripts/temporal_validation/arxiv_temporal_split.py --all-cs
"""

import argparse
import json
import os
from pathlib import Path

# Default: categories most relevant to Linux/x86 TVA corpus
DEFAULT_CATEGORIES = {
    "cs.OS",   # Operating systems
    "cs.AR",   # Hardware architecture
    "cs.PL",   # Programming languages
    "cs.SE",   # Software engineering
    "cs.DC",   # Distributed computing
    "cs.NI",   # Networking
    "cs.CR",   # Cryptography / security
}

ARXIV_SNAPSHOT = Path("data/raw/arxiv/arxiv-metadata-oai-snapshot.json")
OUTPUT_DIR = Path("data/processed/tvv")
SPLIT_YEAR = 2019


def paper_matches_categories(paper: dict, target_cats: set) -> bool:
    cats = paper.get("categories", "")
    return any(c in cats for c in target_cats)


def get_year(paper: dict) -> int:
    date = paper.get("update_date", "")
    try:
        return int(date[:4]) if date and len(date) >= 4 else 0
    except ValueError:
        return 0


def split(categories: set, all_cs: bool):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    train_path = OUTPUT_DIR / "arxiv_train.jsonl"
    val_path = OUTPUT_DIR / "arxiv_val.jsonl"

    if all_cs:
        categories = None  # None = accept any cs.*
        print("Mode: all cs.* categories")
    else:
        print(f"Mode: {sorted(categories)}")

    train_count = val_count = skip_count = 0

    with (
        open(ARXIV_SNAPSHOT) as src,
        open(train_path, "w") as train_f,
        open(val_path, "w") as val_f,
    ):
        for i, line in enumerate(src):
            if i % 200_000 == 0 and i > 0:
                print(f"  {i:,} processed | train={train_count:,} val={val_count:,} skip={skip_count:,}")
            try:
                paper = json.loads(line)
            except json.JSONDecodeError:
                skip_count += 1
                continue

            # Category filter
            if categories is not None:
                if not paper_matches_categories(paper, categories):
                    skip_count += 1
                    continue
            else:
                if "cs." not in paper.get("categories", ""):
                    skip_count += 1
                    continue

            year = get_year(paper)
            if year == 0:
                skip_count += 1
                continue

            # Keep only fields needed for TVV
            record = {
                "id": paper.get("id"),
                "title": paper.get("title", "").replace("\n", " ").strip(),
                "abstract": paper.get("abstract", "").replace("\n", " ").strip(),
                "categories": paper.get("categories"),
                "update_date": paper.get("update_date"),
                "year": year,
            }

            if year < SPLIT_YEAR:
                train_f.write(json.dumps(record) + "\n")
                train_count += 1
            else:
                val_f.write(json.dumps(record) + "\n")
                val_count += 1

    print(f"\nDone.")
    print(f"  Train (t < {SPLIT_YEAR}): {train_count:,}  →  {train_path}")
    print(f"  Val   (t ≥ {SPLIT_YEAR}): {val_count:,}  →  {val_path}")
    print(f"  Skipped: {skip_count:,}")
    return train_count, val_count


def main():
    parser = argparse.ArgumentParser(description="Split arXiv snapshot for TVV experiment")
    parser.add_argument(
        "--categories", nargs="+", default=None,
        help="arXiv categories to include (default: cs.OS cs.AR cs.PL cs.SE cs.DC cs.NI cs.CR)"
    )
    parser.add_argument(
        "--all-cs", action="store_true",
        help="Include all cs.* categories"
    )
    args = parser.parse_args()

    if not ARXIV_SNAPSHOT.exists():
        print(f"ERROR: {ARXIV_SNAPSHOT} not found.")
        return

    cats = set(args.categories) if args.categories else DEFAULT_CATEGORIES
    split(cats, args.all_cs)


if __name__ == "__main__":
    main()
