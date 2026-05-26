"""Learning Path Planning Agent."""

from __future__ import annotations

import logging
from time import perf_counter

from app.agents.state import RecommendationState
from app.learning_path.models import LearningPathRequest
from app.learning_path.planner import LearningPathPlanner
from app.retrieval.semantic import SemanticCourseRetriever
from app.skill_gap.analyzer import SkillGapAnalyzer


logger = logging.getLogger(__name__)


def learning_path_planning_agent(state: RecommendationState) -> RecommendationState:
    """Create a structured path from retrieved courses and skill gaps."""
    started_at = perf_counter()
    retriever = SemanticCourseRetriever()
    skill_gap_analyzer = SkillGapAnalyzer(
        foundational_retriever=retriever,
        foundational_top_k_per_skill=1,
    )
    planner = LearningPathPlanner(skill_gap_analyzer)

    learning_path = planner.plan(
        LearningPathRequest(
            learning_goal=state["query"],
            student_profile=state["student_profile"],
            max_courses=state.get("max_path_courses", 6),
            candidate_k=state.get("top_k", 8),
        ),
        state.get("retrieved_courses", []),
    )

    logger.info(
        "recommendations.learning_path.complete total_ms=%.1f path_courses=%s stages=%s",
        (perf_counter() - started_at) * 1000.0,
        learning_path.total_courses,
        len(learning_path.stages),
    )

    return {
        **state,
        "learning_path": learning_path,
    }
