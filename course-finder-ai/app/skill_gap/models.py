"""Typed models for skill gap analysis."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.retrieval.models import CourseSearchResult


@dataclass(frozen=True)
class StudentProfile:
    """Student skills and goals used to evaluate course readiness."""

    current_skills: list[str] = field(default_factory=list)
    learning_goal: str = ""
    career_goal: str = ""


@dataclass(frozen=True)
class FoundationalCourseRecommendation:
    """A beginner-friendly course recommendation for a missing skill."""

    missing_skill: str
    course_id: str
    title: str
    organization: str
    score: float
    reason: str


@dataclass(frozen=True)
class SkillGapResult:
    """Skill readiness analysis for one target course."""

    course_id: str
    course_title: str
    course_difficulty: str
    inferred_prerequisites: list[str]
    matched_skills: list[str]
    missing_skills: list[str]
    readiness_score: float
    readiness_label: str
    foundational_courses: list[FoundationalCourseRecommendation]
    note: str


@dataclass(frozen=True)
class CourseCandidate:
    """Minimal course shape accepted by the analyzer."""

    course_id: str
    title: str
    organization: str
    difficulty: str
    course_type: str
    skills_text: str
    document: str = ""

    @classmethod
    def from_search_result(cls, result: CourseSearchResult) -> "CourseCandidate":
        metadata = result.metadata
        return cls(
            course_id=result.course_id,
            title=result.title,
            organization=result.organization,
            difficulty=str(metadata.get("difficulty", "")),
            course_type=str(metadata.get("course_type", "")),
            skills_text=str(metadata.get("skills_text", "")),
            document=result.document,
        )
