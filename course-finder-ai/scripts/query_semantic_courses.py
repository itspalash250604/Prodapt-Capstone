"""Run a manual semantic course search from the command line."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.retrieval.semantic import SemanticCourseRetriever


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query the semantic course index.")
    parser.add_argument("query", help="Student learning goal or search query.")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to return.")
    parser.add_argument("--difficulty", help="Optional difficulty metadata filter.")
    parser.add_argument("--course-type", help="Optional course type metadata filter.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    filters = {}
    if args.difficulty:
        filters["difficulty"] = args.difficulty
    if args.course_type:
        filters["course_type"] = args.course_type

    retriever = SemanticCourseRetriever()
    results = retriever.search(args.query, top_k=args.top_k, filters=filters or None)

    for rank, result in enumerate(results, start=1):
        print(f"{rank}. {result.title} ({result.organization})")
        print(f"   score: {result.score:.4f}")
        print(f"   difficulty: {result.metadata.get('difficulty')}")
        print(f"   type: {result.metadata.get('course_type')}")
        print(f"   skills: {result.metadata.get('skills_text')}")
        print()


if __name__ == "__main__":
    main()
