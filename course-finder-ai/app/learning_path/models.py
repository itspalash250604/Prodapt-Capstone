"""Typed models for structured learning paths."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.skill_gap.models import StudentProfile


@dataclass(frozen=True)
class LearningPathRequest:
    """Input needed to build a course learning path."""

    learning_goal: str
    student_profile: StudentProfile
    max_courses: int = 6
    candidate_k: int = 20
    target_difficulty: str | None = None


@dataclass(frozen=True)
class LearningPathCourse:
    """One course included in a learning path stage."""

    course_id: str
    title: str
    organization: str
    difficulty: str
    course_type: str
    skills: list[str]
    reason: str
    relevance_score: float | None = None
    missing_skill: str | None = None


@dataclass(frozen=True)
class LearningPathStage:
    """A stage in a structured learning path."""

    stage_number: int
    title: str
    purpose: str
    courses: list[LearningPathCourse] = field(default_factory=list)


@dataclass(frozen=True)
class LearningPath:
    """Structured course path from foundations to goal-aligned courses."""

    goal: str
    readiness_summary: str
    stages: list[LearningPathStage]
    total_courses: int
    note: str
