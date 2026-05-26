"""Pydantic request and response schemas for API v1."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RecommendationRequest(BaseModel):
    """Request body for full course recommendation orchestration."""

    query: str = Field(..., min_length=3, max_length=500)
    current_skills: list[str] = Field(default_factory=list, max_length=50)
    career_goal: str | None = Field(default=None, max_length=200)
    candidate_k: int = Field(default=20, ge=1, le=50)
    top_k: int = Field(default=8, ge=1, le=20)
    max_path_courses: int = Field(default=6, ge=1, le=12)
    use_reranker: bool = True


class IntakeResponse(BaseModel):
    """Normalized text extracted from uploaded content."""

    source_type: str
    filename: str | None = None
    text: str
    current_skills: list[str] = Field(default_factory=list)
    career_goal: str | None = None
    learning_intent: list[str] = Field(default_factory=list)
    career_goals: list[str] = Field(default_factory=list)
    semantic_chunks: list[str] = Field(default_factory=list)
    confidence_score: float = 0.0
    page_count: int | None = None
    duration_seconds: float | None = None
    model_name: str | None = None
    language: str | None = None
    transcription_engine: str | None = None


class CourseResponse(BaseModel):
    """Course returned by retrieval/reranking."""

    course_id: str
    title: str
    organization: str
    score: float
    metadata: dict[str, Any]
    # Human-friendly course description (prefer metadata.description or document snippet)
    description: str | None = None
    # Why this course was selected for this learner (LLM-generated rationale)
    rationale: str | None = None
    # Human-friendly estimate of time required to complete the course (e.g. "6 weeks", "12 hours")
    time_to_complete: str | None = None
    # Normalized match percentage (0.0 - 1.0). Mirrors `score` but explicit for UI.
    match_percentage: float | None = None
    # Preparatory resources for inferred missing prerequisites. Each item contains
    # a `skill` and a list of `resources` (title, url, source, estimated_time).
    preparatory_resources: list[dict[str, Any]] | None = Field(default_factory=list)


class RecommendationResponse(BaseModel):
    """Full response returned by the recommendation endpoint."""

    query: str
    courses: list[CourseResponse]
    skill_gaps: list[dict[str, Any]]
    learning_path: dict[str, Any] | None
    career_alignment: dict[str, Any] | None
    guardrails: dict[str, Any] | None
    # Non-error quality/readiness signals produced by guardrail checks (warnings/info)
    quality_issues: list[dict[str, Any]] | None = Field(default_factory=list)
    final_response: str

    model_config = ConfigDict(arbitrary_types_allowed=True)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
