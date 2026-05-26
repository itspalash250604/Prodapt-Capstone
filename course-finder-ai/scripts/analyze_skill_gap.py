"""Analyze skill gaps for the top retrieved course for a learning goal."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.retrieval.semantic import SemanticCourseRetriever
from app.skill_gap.analyzer import SkillGapAnalyzer
from app.skill_gap.models import StudentProfile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze course readiness and missing skills.")
    parser.add_argument("course_query", help="Course or learning goal to retrieve as the target course.")
    parser.add_argument(
        "--skills",
        default="",
        help="Comma-separated list of skills the student already has.",
    )
    parser.add_argument("--candidate-rank", type=int, default=1, help="Which retrieved course to analyze.")
    parser.add_argument("--foundational-top-k", type=int, default=2)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    current_skills = [skill.strip() for skill in args.skills.split(",") if skill.strip()]

    retriever = SemanticCourseRetriever()
    candidates = retriever.search(args.course_query, top_k=max(args.candidate_rank, 1))
    target_course = candidates[args.candidate_rank - 1]

    analyzer = SkillGapAnalyzer(
        foundational_retriever=retriever,
        foundational_top_k_per_skill=args.foundational_top_k,
    )
    result = analyzer.analyze(
        StudentProfile(current_skills=current_skills, learning_goal=args.course_query),
        target_course,
    )

    print(f"Target course: {result.course_title}")
    print(f"Difficulty: {result.course_difficulty}")
    print(f"Readiness: {result.readiness_label} ({result.readiness_score:.0%})")
    print()
    print("Inferred preparation skills:")
    for skill in result.inferred_prerequisites or ["None inferred"]:
        print(f"- {skill}")
    print()
    print("Matched skills:")
    for skill in result.matched_skills or ["None"]:
        print(f"- {skill}")
    print()
    print("Missing skills:")
    for skill in result.missing_skills or ["None"]:
        print(f"- {skill}")
    print()
    print("Foundational course suggestions:")
    for recommendation in result.foundational_courses or []:
        print(
            f"- {recommendation.missing_skill}: "
            f"{recommendation.title} ({recommendation.organization})"
        )
    if not result.foundational_courses:
        print("- None")
    print()
    print(result.note)


if __name__ == "__main__":
    main()
