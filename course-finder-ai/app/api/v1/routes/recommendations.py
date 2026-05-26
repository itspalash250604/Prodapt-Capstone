"""Course recommendation routes."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
import logging
from time import perf_counter
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.agents.advisor_agent import generate_course_enrichment
from app.agents.graph import build_recommendation_graph
from app.api.v1.schemas import CourseResponse, RecommendationRequest, RecommendationResponse
from app.skill_gap.models import StudentProfile


logger = logging.getLogger(__name__)


router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("", response_model=RecommendationResponse)
def recommend_courses(request: RecommendationRequest) -> RecommendationResponse:
    request_started_at = perf_counter()
    if request.top_k > request.candidate_k:
        raise HTTPException(
            status_code=422,
            detail="top_k must be less than or equal to candidate_k.",
        )

    logger.info(
        "recommendations.request.start query=%r candidate_k=%s top_k=%s max_path_courses=%s use_reranker=%s",
        request.query,
        request.candidate_k,
        request.top_k,
        request.max_path_courses,
        request.use_reranker,
    )

    graph_build_started_at = perf_counter()
    graph = build_recommendation_graph()
    graph_build_elapsed = perf_counter() - graph_build_started_at

    invoke_started_at = perf_counter()
    final_state = graph.invoke(
        {
            "query": request.query,
            "student_profile": StudentProfile(
                current_skills=request.current_skills,
                learning_goal=request.query,
                career_goal=request.career_goal or request.query,
            ),
            "career_goal": request.career_goal or request.query,
            "candidate_k": request.candidate_k,
            "top_k": request.top_k,
            "max_path_courses": request.max_path_courses,
            "use_reranker": request.use_reranker,
        }
    )
    invoke_elapsed = perf_counter() - invoke_started_at

    enrichment_started_at = perf_counter()
    retrieved_courses = list(final_state.get("retrieved_courses", [])) or []
    enriched_courses = []
    for course in retrieved_courses:
        enrichment = generate_course_enrichment(course, final_state)
        enriched_courses.append((course, enrichment))
    enrichment_elapsed = perf_counter() - enrichment_started_at

    logger.info(
        (
            "recommendations.request.complete total_ms=%.1f graph_build_ms=%.1f invoke_ms=%.1f "
            "enrichment_ms=%.1f retrieved=%s skill_gaps=%s learning_path=%s career_alignment=%s guardrails=%s"
        ),
        (perf_counter() - request_started_at) * 1000.0,
        graph_build_elapsed * 1000.0,
        invoke_elapsed * 1000.0,
        enrichment_elapsed * 1000.0,
        len(retrieved_courses),
        len(final_state.get("skill_gap_results", []) or []),
        bool(final_state.get("learning_path")),
        bool(final_state.get("career_alignment")),
        bool(final_state.get("guardrail_report")),
    )

    try:
        return RecommendationResponse(
            query=request.query,
            courses=[
                CourseResponse(
                    course_id=course.course_id,
                    title=course.title,
                    organization=course.organization,
                    score=course.score,
                    metadata=course.metadata,
                    description=enrichment.get("description"),
                    rationale=enrichment.get("rationale"),
                    time_to_complete=enrichment.get("time_to_complete"),
                    match_percentage=enrichment.get("match_percentage"),
                    preparatory_resources=enrichment.get("preparatory_resources"),
                )
                for course, enrichment in enriched_courses
            ],
            skill_gaps=[to_plain_data(item) for item in final_state.get("skill_gap_results", [])],
            learning_path=to_plain_data(final_state.get("learning_path")),
            career_alignment=to_plain_data(final_state.get("career_alignment")),
            guardrails=to_plain_data(final_state.get("guardrail_report")),
            quality_issues=to_plain_data(final_state.get("quality_issues")),
            final_response=final_state.get("final_response", ""),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to serialize recommendation response: {exc}",
        ) from exc


def to_plain_data(value: Any) -> Any:
    """Convert dataclasses and nested containers into JSON-friendly data."""
    if value is None:
        return None
    if is_dataclass(value):
        return {
            key: to_plain_data(item)
            for key, item in asdict(value).items()
        }
    if isinstance(value, list):
        return [to_plain_data(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): to_plain_data(item)
            for key, item in value.items()
        }
    return value
