"""DeepEval-compatible deterministic metrics for course recommendations."""

from __future__ import annotations

import json
import re
from typing import Any

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class SnapshotMetric(BaseMetric):
    """Base class for deterministic metrics over JSON recommendation snapshots."""

    metric_name = "Snapshot Metric"

    def __init__(self, threshold: float = 0.7) -> None:
        self.threshold = threshold
        self.score = 0.0
        self.reason = ""
        self.success = False
        self.error = None
        self.evaluation_model = "deterministic"
        self.include_reason = True
        self.strict_mode = False
        self.async_mode = False

    def measure(self, test_case: LLMTestCase) -> float:
        try:
            snapshot = parse_snapshot(test_case.actual_output)
            expected = parse_expected(test_case.expected_output)
            self.score, self.reason = self.score_snapshot(snapshot, expected)
            self.success = self.score >= self.threshold
            return self.score
        except Exception as exc:
            self.error = str(exc)
            raise

    async def a_measure(self, test_case: LLMTestCase) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        if self.error is not None:
            self.success = False
        else:
            self.success = self.score >= self.threshold
        return self.success

    @property
    def __name__(self) -> str:
        return self.metric_name

    def score_snapshot(
        self,
        snapshot: dict[str, Any],
        expected: dict[str, Any],
    ) -> tuple[float, str]:
        raise NotImplementedError


class RecommendationRelevanceMetric(SnapshotMetric):
    """Checks whether retrieved courses match expected skills or keywords."""

    metric_name = "Recommendation Relevance"

    def score_snapshot(
        self,
        snapshot: dict[str, Any],
        expected: dict[str, Any],
    ) -> tuple[float, str]:
        courses = snapshot.get("retrieved_courses", [])
        if not courses:
            return 0.0, "No courses were retrieved."

        expected_terms = normalize_terms(
            expected.get("expected_skills", []) + expected.get("expected_course_keywords", [])
        )
        if not expected_terms:
            return 1.0, "No expected relevance terms were provided."

        relevant_count = 0
        for course in courses:
            course_text = normalize_text(
                " ".join(
                    [
                        course.get("title", ""),
                        course.get("organization", ""),
                        str(course.get("metadata", {}).get("skills_text", "")),
                    ]
                )
            )
            if any(term in course_text for term in expected_terms):
                relevant_count += 1

        score = relevant_count / len(courses)
        return round(score, 2), f"{relevant_count}/{len(courses)} courses matched expected relevance terms."


class HallucinationGroundingMetric(SnapshotMetric):
    """Checks whether advisor output names only courses present in retrieved/path data."""

    metric_name = "Hallucination Grounding"

    def score_snapshot(
        self,
        snapshot: dict[str, Any],
        expected: dict[str, Any],
    ) -> tuple[float, str]:
        known_titles = known_course_titles(snapshot)
        response = snapshot.get("final_response", "")
        if not response.strip():
            return 0.0, "Final response is empty."

        suspicious_titles = []
        for line in response.splitlines():
            if not is_course_bullet_line(line):
                continue
            stripped = line.strip(" -0123456789.[]")
            title = stripped.split(" (")[0].strip()
            if looks_like_course_title(title) and not is_known_title(title, known_titles):
                suspicious_titles.append(title)

        if suspicious_titles:
            return 0.0, f"Response mentioned unknown course titles: {suspicious_titles[:5]}."
        return 1.0, "Final response is grounded in retrieved or path courses."


class PrerequisiteCorrectnessMetric(SnapshotMetric):
    """Checks prerequisite validation and missing-skill handling."""

    metric_name = "Prerequisite Correctness"

    def score_snapshot(
        self,
        snapshot: dict[str, Any],
        expected: dict[str, Any],
    ) -> tuple[float, str]:
        guardrail_issues = snapshot.get("guardrail_report", {}).get("issues", [])
        prereq_issues = [
            issue
            for issue in guardrail_issues
            if issue.get("check_name") == "prerequisite_validation"
        ]
        skill_gaps = snapshot.get("skill_gap_results", [])
        if not skill_gaps:
            return 0.0, "No skill gap results were produced."

        severe_penalty = sum(1 for issue in prereq_issues if issue.get("severity") == "error")
        warning_penalty = sum(1 for issue in prereq_issues if issue.get("severity") == "warning")
        score = max(0.0, 1.0 - severe_penalty - (warning_penalty * 0.1))
        return round(score, 2), f"Found {len(prereq_issues)} prerequisite guardrail issue(s)."


class LearningPathQualityMetric(SnapshotMetric):
    """Checks path size, stage structure, and guardrail quality."""

    metric_name = "Learning Path Quality"

    def score_snapshot(
        self,
        snapshot: dict[str, Any],
        expected: dict[str, Any],
    ) -> tuple[float, str]:
        path = snapshot.get("learning_path")
        if not path:
            return 0.0, "Learning path is missing."

        total_courses = int(path.get("total_courses", 0))
        max_courses = int(expected.get("max_path_courses", 6))
        stages = path.get("stages", [])
        guardrail_report = snapshot.get("guardrail_report", {})
        errors = [
            issue
            for issue in guardrail_report.get("issues", [])
            if issue.get("severity") == "error"
        ]

        score = 1.0
        reasons = []
        if total_courses == 0:
            score -= 0.5
            reasons.append("path has no courses")
        if total_courses > max_courses:
            score -= 0.4
            reasons.append("path exceeds max_courses")
        if not stages:
            score -= 0.3
            reasons.append("path has no stages")
        if errors:
            score -= 0.4
            reasons.append(f"{len(errors)} guardrail error(s)")

        score = max(0.0, score)
        if not reasons:
            reasons.append("path has valid size, stages, and no guardrail errors")
        return round(score, 2), "; ".join(reasons)


def parse_snapshot(actual_output: str | None) -> dict[str, Any]:
    if not actual_output:
        return {}
    return json.loads(actual_output)


def parse_expected(expected_output: str | None) -> dict[str, Any]:
    if not expected_output:
        return {}
    return json.loads(expected_output)


def normalize_terms(terms: list[str]) -> list[str]:
    return [normalize_text(term) for term in terms if term.strip()]


def normalize_text(value: str) -> str:
    text = re.sub(r"[^a-z0-9+#. ]+", " ", value.casefold())
    return re.sub(r"\s+", " ", text).strip()


def known_course_titles(snapshot: dict[str, Any]) -> set[str]:
    titles = {
        course.get("title", "").casefold()
        for course in snapshot.get("retrieved_courses", [])
    }
    path = snapshot.get("learning_path") or {}
    for stage in path.get("stages", []):
        for course in stage.get("courses", []):
            titles.add(course.get("title", "").casefold())
    return {title for title in titles if title}


def looks_like_course_title(value: str) -> bool:
    if len(value.split()) < 2:
        return False
    return any(char.isupper() for char in value)


def is_course_bullet_line(line: str) -> bool:
    stripped = line.strip()
    if re.match(r"^-\s+(INFO|WARNING|ERROR)\s+\[", stripped):
        return False
    return bool(re.match(r"^(\d+\.|-)\s+.+\(.+\)", stripped))


def is_known_title(title: str, known_titles: set[str]) -> bool:
    normalized_title = title.casefold()
    return any(
        known == normalized_title
        or known.startswith(normalized_title)
        or normalized_title.startswith(known)
        for known in known_titles
    )
