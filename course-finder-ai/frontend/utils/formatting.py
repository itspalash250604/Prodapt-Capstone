"""Formatting helpers for Streamlit components."""

from __future__ import annotations

from typing import Any


def format_score(value: Any) -> str:
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return "N/A"


def format_rating(value: Any) -> str:
    try:
        return f"{float(value):.1f}/5"
    except (TypeError, ValueError):
        return "N/A"


def split_skills(skills_text: str | None, limit: int | None = None) -> list[str]:
    if not skills_text:
        return []
    skills = [skill.strip() for skill in skills_text.replace("|", ",").split(",") if skill.strip()]
    if limit is not None:
        return skills[:limit]
    return skills


def as_percent(value: Any) -> str:
    try:
        return f"{float(value) * 100:.0f}%"
    except (TypeError, ValueError):
        return "N/A"


def compact_list(values: list[str], empty: str = "None") -> str:
    return ", ".join(values) if values else empty
