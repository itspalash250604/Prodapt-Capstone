"""Unit tests for recommendation guardrails."""

from __future__ import annotations

import unittest

from app.agents.state import CareerAlignment
from app.guardrails.validators import RecommendationGuardrails
from app.learning_path.models import LearningPath, LearningPathCourse, LearningPathStage


class RecommendationGuardrailsTest(unittest.TestCase):
    def test_valid_path_passes(self) -> None:
        path = _path(
            [
                _stage(1, "Foundations", [_course("foundation", "Intro Statistics", "Beginner", missing_skill="General Statistics")]),
                _stage(2, "Core Learning", [_course("core", "Machine Learning", "Intermediate")]),
            ]
        )

        report = RecommendationGuardrails().validate(path, max_courses=3)

        self.assertTrue(report.passed)
        self.assertEqual(report.error_count, 0)

    def test_duplicate_course_is_error(self) -> None:
        path = _path(
            [
                _stage(1, "Core Learning", [_course("same", "Course A", "Beginner")]),
                _stage(2, "Advanced Growth", [_course("same", "Course A", "Intermediate")]),
            ]
        )

        report = RecommendationGuardrails().validate(path, max_courses=3)

        self.assertFalse(report.passed)
        self.assertTrue(any(issue.check_name == "sequence_validation" for issue in report.issues))

    def test_max_courses_violation_is_error(self) -> None:
        path = _path(
            [
                _stage(1, "Core Learning", [_course("one", "One", "Beginner")]),
                _stage(2, "Core Learning", [_course("two", "Two", "Beginner")]),
            ]
        )

        report = RecommendationGuardrails().validate(path, max_courses=1)

        self.assertFalse(report.passed)
        self.assertIn("exceeds max_courses", report.summary + " ".join(issue.message for issue in report.issues))

    def test_weak_alignment_is_warning(self) -> None:
        path = _path([_stage(1, "Core Learning", [_course("weak", "Weak Match", "Beginner", relevance_score=0.2)])])
        alignment: CareerAlignment = {
            "career_goal": "machine learning engineer",
            "matched_skill_clusters": ["Machine Learning"],
            "course_alignment": [{"course_id": "weak", "title": "Weak Match", "matched_career_skills": []}],
            "summary": "test",
        }

        report = RecommendationGuardrails().validate(path, career_alignment=alignment, max_courses=2)

        self.assertTrue(report.passed)
        self.assertTrue(any(issue.check_name == "learning_objective_alignment" for issue in report.issues))


def _path(stages: list[LearningPathStage]) -> LearningPath:
    return LearningPath(
        goal="test goal",
        readiness_summary="test",
        stages=stages,
        total_courses=sum(len(stage.courses) for stage in stages),
        note="test",
    )


def _stage(
    stage_number: int,
    title: str,
    courses: list[LearningPathCourse],
) -> LearningPathStage:
    return LearningPathStage(
        stage_number=stage_number,
        title=title,
        purpose="test",
        courses=courses,
    )


def _course(
    course_id: str,
    title: str,
    difficulty: str,
    missing_skill: str | None = None,
    relevance_score: float | None = 0.8,
) -> LearningPathCourse:
    return LearningPathCourse(
        course_id=course_id,
        title=title,
        organization="Example University",
        difficulty=difficulty,
        course_type="Course",
        skills=["Machine Learning"],
        reason="Included for testing.",
        relevance_score=relevance_score,
        missing_skill=missing_skill,
    )


if __name__ == "__main__":
    unittest.main()
