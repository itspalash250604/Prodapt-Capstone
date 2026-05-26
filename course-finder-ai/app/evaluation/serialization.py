"""Serialization helpers for recommendation graph outputs."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


def to_plain_data(value: Any) -> Any:
    """Convert dataclasses and nested containers into JSON-friendly data."""
    if value is None:
        return None
    if is_dataclass(value):
        return {key: to_plain_data(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [to_plain_data(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_plain_data(item) for key, item in value.items()}
    return value


def recommendation_state_snapshot(state: dict[str, Any]) -> dict[str, Any]:
    """Create a compact snapshot from graph state for evaluation metrics."""
    courses = state.get("retrieved_courses", [])
    learning_path = state.get("learning_path")
    guardrail_report = state.get("guardrail_report")

    return {
        "query": state.get("query", ""),
        "retrieved_courses": [
            {
                "course_id": course.course_id,
                "title": course.title,
                "organization": course.organization,
                "score": course.score,
                "metadata": to_plain_data(course.metadata),
            }
            for course in courses
        ],
        "skill_gap_results": to_plain_data(state.get("skill_gap_results", [])),
        "learning_path": to_plain_data(learning_path),
        "career_alignment": to_plain_data(state.get("career_alignment")),
        "guardrail_report": to_plain_data(guardrail_report),
        "final_response": state.get("final_response", ""),
    }
