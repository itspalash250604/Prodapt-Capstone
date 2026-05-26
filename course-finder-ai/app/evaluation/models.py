"""Typed models for evaluation cases and reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EvaluationCase:
    """One recommendation evaluation scenario."""

    name: str
    query: str
    current_skills: list[str] = field(default_factory=list)
    career_goal: str = ""
    expected_skills: list[str] = field(default_factory=list)
    expected_course_keywords: list[str] = field(default_factory=list)
    max_path_courses: int = 6
    candidate_k: int = 12
    top_k: int = 5
    use_reranker: bool = False


@dataclass(frozen=True)
class MetricScore:
    """Score produced by one evaluation metric."""

    name: str
    score: float
    success: bool
    reason: str


@dataclass(frozen=True)
class EvaluationReport:
    """Evaluation output for one scenario."""

    case_name: str
    query: str
    metric_scores: list[MetricScore]
    passed: bool
    snapshot: dict[str, Any]
