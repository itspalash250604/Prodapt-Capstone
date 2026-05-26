"""Shared LangGraph state for the recommendation workflow."""

from __future__ import annotations

from typing import Any, TypedDict

from app.guardrails.models import GuardrailReport
from app.learning_path.models import LearningPath
from app.retrieval.models import CourseSearchResult
from app.skill_gap.models import SkillGapResult, StudentProfile


class CareerAlignment(TypedDict, total=False):
    """Career alignment summary produced by the career agent."""

    career_goal: str
    matched_skill_clusters: list[str]
    course_alignment: list[dict[str, Any]]
    alignment_score: float
    score: float
    summary: str


class RecommendationState(TypedDict, total=False):
    """State passed between all recommendation graph agents."""

    query: str
    student_profile: StudentProfile
    career_goal: str
    candidate_k: int
    top_k: int
    max_path_courses: int
    use_reranker: bool

    retrieved_courses: list[CourseSearchResult]
    skill_gap_results: list[SkillGapResult]
    learning_path: LearningPath
    career_alignment: CareerAlignment
    guardrail_report: GuardrailReport
    quality_issues: list[dict[str, Any]]
    final_response: str
