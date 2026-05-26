"""Unit tests for deterministic learning path planning."""

from __future__ import annotations

import unittest

from app.learning_path.models import LearningPathRequest
from app.learning_path.planner import LearningPathPlanner
from app.retrieval.models import CourseSearchResult
from app.skill_gap.models import (
    FoundationalCourseRecommendation,
    SkillGapResult,
    StudentProfile,
)


class StubSkillGapAnalyzer:
    def analyze(self, student_profile, course):
        return SkillGapResult(
            course_id=course.course_id,
            course_title=course.title,
            course_difficulty=str(course.metadata.get("difficulty", "")),
            inferred_prerequisites=["General Statistics"],
            matched_skills=[],
            missing_skills=["General Statistics"],
            readiness_score=0.4,
            readiness_label="needs_preparation",
            foundational_courses=[
                FoundationalCourseRecommendation(
                    missing_skill="General Statistics",
                    course_id="foundation-statistics",
                    title="Introduction to Statistics",
                    organization="Example University",
                    score=0.9,
                    reason="Recommended because it can help build preparation in General Statistics.",
                )
            ],
            note="test",
        )


class LearningPathPlannerTest(unittest.TestCase):
    def test_path_respects_max_courses_and_adds_foundation_first(self) -> None:
        planner = LearningPathPlanner(StubSkillGapAnalyzer())
        request = LearningPathRequest(
            learning_goal="machine learning",
            student_profile=StudentProfile(current_skills=[]),
            max_courses=3,
            candidate_k=3,
        )

        path = planner.plan(request, [_candidate("ml-1", "Machine Learning", "Intermediate", 0.9)])

        self.assertEqual(path.total_courses, 2)
        self.assertEqual(path.stages[0].title, "Foundations")
        self.assertEqual(path.stages[0].courses[0].course_id, "foundation-statistics")

    def test_goal_courses_prioritize_relevance_before_difficulty(self) -> None:
        planner = LearningPathPlanner(StubSkillGapAnalyzer())
        request = LearningPathRequest(
            learning_goal="machine learning engineer",
            student_profile=StudentProfile(current_skills=[]),
            max_courses=2,
            candidate_k=2,
        )
        candidates = [
            _candidate("weak-beginner", "Weak Beginner Match", "Beginner", 0.2),
            _candidate("strong-intermediate", "Strong ML Match", "Intermediate", 0.95),
        ]

        path = planner.plan(request, candidates)
        selected_ids = [
            course.course_id
            for stage in path.stages
            for course in stage.courses
        ]

        self.assertIn("strong-intermediate", selected_ids)
        self.assertNotIn("weak-beginner", selected_ids)


def _candidate(
    course_id: str,
    title: str,
    difficulty: str,
    score: float,
) -> CourseSearchResult:
    return CourseSearchResult(
        course_id=course_id,
        title=title,
        organization="Example University",
        score=score,
        metadata={
            "difficulty": difficulty,
            "course_type": "Course",
            "skills_text": "Machine Learning, Python Programming",
        },
        document="Course text",
    )


if __name__ == "__main__":
    unittest.main()
