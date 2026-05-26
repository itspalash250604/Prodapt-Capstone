"""Skill Gap Analysis Agent."""

from __future__ import annotations

import logging
from time import perf_counter

from app.agents.state import RecommendationState
from app.retrieval.semantic import SemanticCourseRetriever
from app.skill_gap.analyzer import SkillGapAnalyzer


logger = logging.getLogger(__name__)


def skill_gap_analysis_agent(state: RecommendationState) -> RecommendationState:
    """Analyze missing preparation skills for retrieved courses."""
    started_at = perf_counter()
    student_profile = state["student_profile"]
    courses = state.get("retrieved_courses", [])

    retriever = SemanticCourseRetriever()
    analyzer = SkillGapAnalyzer(
        foundational_retriever=retriever,
        foundational_top_k_per_skill=1,
    )
    skill_gap_results = [
        analyzer.analyze(student_profile, course)
        for course in courses
    ]

    logger.info(
        "recommendations.skill_gap.complete total_ms=%.1f courses=%s outputs=%s",
        (perf_counter() - started_at) * 1000.0,
        len(courses),
        len(skill_gap_results),
    )

    return {
        **state,
        "skill_gap_results": skill_gap_results,
    }
