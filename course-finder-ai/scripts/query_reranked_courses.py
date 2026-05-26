"""Run semantic retrieval followed by cross-encoder reranking."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.retrieval.reranker import CrossEncoderCourseReranker
from app.retrieval.semantic import SemanticCourseRetriever


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query and rerank course recommendations.")
    parser.add_argument("query", help="Student learning goal or search query.")
    parser.add_argument("--candidate-k", type=int, default=20, help="Candidates to retrieve before reranking.")
    parser.add_argument("--top-k", type=int, default=5, help="Final reranked results to return.")
    parser.add_argument("--difficulty", help="Optional difficulty metadata filter.")
    parser.add_argument("--course-type", help="Optional course type metadata filter.")
    parser.add_argument(
        "--show-before",
        action="store_true",
        help="Show semantic-only ranking before reranking.",
    )
    return parser.parse_args()


def build_filters(args: argparse.Namespace) -> dict[str, str] | None:
    filters = {}
    if args.difficulty:
        filters["difficulty"] = args.difficulty
    if args.course_type:
        filters["course_type"] = args.course_type
    return filters or None


def print_results(title: str, results: list, show_rerank: bool) -> None:
    print(title)
    print("=" * len(title))
    for rank, result in enumerate(results, start=1):
        print(f"{rank}. {result.title} ({result.organization})")
        if show_rerank:
            print(f"   rerank_score: {result.score:.4f}")
            print(f"   semantic_score: {result.metadata.get('semantic_score'):.4f}")
        else:
            print(f"   semantic_score: {result.score:.4f}")
        print(f"   difficulty: {result.metadata.get('difficulty')}")
        print(f"   type: {result.metadata.get('course_type')}")
        print(f"   skills: {result.metadata.get('skills_text')}")
        print()


def main() -> None:
    args = parse_args()
    if args.candidate_k < args.top_k:
        raise ValueError("--candidate-k should be greater than or equal to --top-k")

    filters = build_filters(args)
    retriever = SemanticCourseRetriever()
    candidates = retriever.search(args.query, top_k=args.candidate_k, filters=filters)

    if args.show_before:
        print_results("Semantic Candidates", candidates[: args.top_k], show_rerank=False)

    reranker = CrossEncoderCourseReranker()
    results = reranker.rerank(args.query, candidates, top_k=args.top_k)
    print_results("Reranked Results", results, show_rerank=True)


if __name__ == "__main__":
    main()
