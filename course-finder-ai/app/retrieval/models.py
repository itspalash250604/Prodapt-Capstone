"""Typed data structures returned by retrieval components."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CourseSearchResult:
    """One course returned by a retriever."""

    course_id: str
    title: str
    organization: str
    score: float
    metadata: dict[str, Any]
    document: str
