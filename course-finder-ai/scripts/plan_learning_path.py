"""Generate a structured learning path for a student goal."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.learning_path.models import LearningPathRequest
from app.learning_path.planner import LearningPathPlanner
from app.retrieval.reranker import CrossEncoderCourseReranker
from app.retrieval.semantic import SemanticCourseRetriever
from app.skill_gap.analyzer import SkillGapAnalyzer
from app.skill_gap.models import StudentProfile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan a structured course learning path.")
    parser.add_argument("goal", help="Student learning or career goal.")
    parser.add_argument(
        "--skills",
        default="",
        help="Comma-separated list of skills the student already has.",
    )
    parser.add_argument("--candidate-k", type=int, default=20)
    parser.add_argument("--top-k", type=int, default=10, help="Reranked candidates to plan from.")
    parser.add_argument("--max-courses", type=int, default=6)
    parser.add_argument("--target-difficulty", help="Optional maximum target difficulty.")
    parser.add_argument(
        "--skip-rerank",
        action="store_true",
        help="Use semantic ranking only. Faster, but usually lower quality.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    current_skills = [skill.strip() for skill in args.skills.split(",") if skill.strip()]

    retriever = SemanticCourseRetriever()
    candidates = retriever.search(args.goal, top_k=args.candidate_k)

    if not args.skip_rerank:
        reranker = CrossEncoderCourseReranker()
        candidates = reranker.rerank(args.goal, candidates, top_k=args.top_k)
    else:
        candidates = candidates[: args.top_k]

    student_profile = StudentProfile(
        current_skills=current_skills,
        learning_goal=args.goal,
        career_goal=args.goal,
    )
    skill_gap_analyzer = SkillGapAnalyzer(
        foundational_retriever=retriever,
        foundational_top_k_per_skill=1,
    )
    planner = LearningPathPlanner(skill_gap_analyzer)
    learning_path = planner.plan(
        LearningPathRequest(
            learning_goal=args.goal,
            student_profile=student_profile,
            max_courses=args.max_courses,
            candidate_k=args.top_k,
            target_difficulty=args.target_difficulty,
        ),
        candidates,
    )

    print(f"Goal: {learning_path.goal}")
    print(f"Total courses: {learning_path.total_courses}")
    print(f"Readiness: {learning_path.readiness_summary}")
    print()

    for stage in learning_path.stages:
        print(f"Stage {stage.stage_number}: {stage.title}")
        print(f"Purpose: {stage.purpose}")
        for course in stage.courses:
            extra = f" | fills: {course.missing_skill}" if course.missing_skill else ""
            print(
                f"- {course.title} ({course.organization}) "
                f"[{course.difficulty}, {course.course_type}]{extra}"
            )
            print(f"  Reason: {course.reason}")
        print()

    print(learning_path.note)


if __name__ == "__main__":
    main()
