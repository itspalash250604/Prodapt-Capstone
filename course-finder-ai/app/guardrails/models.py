"""Typed models for recommendation guardrail validation."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GuardrailIssue:
    """One validation issue found in a recommendation output."""

    check_name: str
    severity: str
    message: str
    course_id: str | None = None
    stage_number: int | None = None


@dataclass(frozen=True)
class GuardrailReport:
    """Structured validation report for a recommendation output."""

    passed: bool
    issues: list[GuardrailIssue] = field(default_factory=list)
    summary: str = ""

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "warning")
