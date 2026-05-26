"""Guardrails Agent."""

from __future__ import annotations

import logging
from time import perf_counter

from app.agents.state import RecommendationState
from app.guardrails.validators import RecommendationGuardrails


logger = logging.getLogger(__name__)


def guardrails_agent(state: RecommendationState) -> RecommendationState:
    """Validate the generated recommendation before advisor synthesis."""
    started_at = perf_counter()
    guardrails = RecommendationGuardrails()
    report = guardrails.validate(
        learning_path=state.get("learning_path"),
        skill_gap_results=state.get("skill_gap_results", []),
        career_alignment=state.get("career_alignment"),
        max_courses=state.get("max_path_courses"),
    )

    # Also collect non-error quality/readiness signals (warnings/info) so the
    # API can surface them separately from strict guardrails.
    all_issues = guardrails.run_checks(
        learning_path=state.get("learning_path"),
        skill_gap_results=state.get("skill_gap_results", []),
        career_alignment=state.get("career_alignment"),
        max_courses=state.get("max_path_courses"),
    )

    quality_issues = [
        {
            "check_name": issue.check_name,
            "severity": issue.severity,
            "message": issue.message,
            "course_id": issue.course_id,
            "stage_number": issue.stage_number,
        }
        for issue in all_issues
        if issue.severity != "error"
    ]

    logger.info(
        "recommendations.guardrails.complete total_ms=%.1f issues=%s quality_issues=%s",
        (perf_counter() - started_at) * 1000.0,
        len(report.issues),
        len(quality_issues),
    )

    return {
        **state,
        "guardrail_report": report,
        "quality_issues": quality_issues,
    }
