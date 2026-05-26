"""Unit tests for deterministic skill gap logic."""

from __future__ import annotations

import unittest

from app.skill_gap.analyzer import SkillGapAnalyzer
from app.skill_gap.models import CourseCandidate, StudentProfile


class SkillGapAnalyzerTest(unittest.TestCase):
    def test_partial_readiness_detects_missing_prerequisites(self) -> None:
        analyzer = SkillGapAnalyzer()
        course = CourseCandidate(
            course_id="course-1",
            title="Applied Machine Learning in Python",
            organization="Example University",
            difficulty="Intermediate",
            course_type="Course",
            skills_text="Machine Learning, Python Programming, Data Analysis",
        )
        profile = StudentProfile(current_skills=["Python", "Data Analysis"])

        result = analyzer.analyze(profile, course)

        self.assertEqual(result.readiness_label, "needs_preparation")
        self.assertIn("General Statistics", result.missing_skills)
        self.assertIn("Python Programming", result.matched_skills)

    def test_ready_when_all_inferred_prerequisites_are_present(self) -> None:
        analyzer = SkillGapAnalyzer()
        course = CourseCandidate(
            course_id="course-2",
            title="Applied Machine Learning in Python",
            organization="Example University",
            difficulty="Intermediate",
            course_type="Course",
            skills_text="Machine Learning, Python Programming, Data Analysis",
        )
        profile = StudentProfile(
            current_skills=[
                "Python Programming",
                "Data Analysis",
                "General Statistics",
                "Computer Programming",
                "Spreadsheet Software",
            ]
        )

        result = analyzer.analyze(profile, course)

        self.assertEqual(result.readiness_label, "ready")
        self.assertEqual(result.missing_skills, [])
        self.assertEqual(result.readiness_score, 1.0)


if __name__ == "__main__":
    unittest.main()
