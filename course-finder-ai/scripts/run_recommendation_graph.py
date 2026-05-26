"""Run the LangGraph multi-agent recommendation workflow."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.graph import build_recommendation_graph
from app.skill_gap.models import StudentProfile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the multi-agent course recommendation graph.")
    parser.add_argument("query", help="Student learning goal or course search request.")
    parser.add_argument("--skills", default="", help="Comma-separated student skills.")
    parser.add_argument("--career-goal", default="", help="Optional explicit career goal.")
    parser.add_argument("--candidate-k", type=int, default=20)
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--max-path-courses", type=int, default=6)
    parser.add_argument("--skip-rerank", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    current_skills = [skill.strip() for skill in args.skills.split(",") if skill.strip()]
    graph = build_recommendation_graph()

    final_state = graph.invoke(
        {
            "query": args.query,
            "student_profile": StudentProfile(
                current_skills=current_skills,
                learning_goal=args.query,
                career_goal=args.career_goal or args.query,
            ),
            "career_goal": args.career_goal or args.query,
            "candidate_k": args.candidate_k,
            "top_k": args.top_k,
            "max_path_courses": args.max_path_courses,
            "use_reranker": not args.skip_rerank,
        }
    )

    print(final_state["final_response"])


if __name__ == "__main__":
    main()
