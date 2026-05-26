"""Unit tests for recommendation evaluation metrics."""

from __future__ import annotations

import json
import unittest

from deepeval.test_case import LLMTestCase

from app.evaluation.metrics import (
    HallucinationGroundingMetric,
    LearningPathQualityMetric,
    PrerequisiteCorrectnessMetric,
    RecommendationRelevanceMetric,
)


class EvaluationMetricsTest(unittest.TestCase):
    def test_recommendation_relevance_scores_expected_skill_matches(self) -> None:
        metric = RecommendationRelevanceMetric(threshold=0.5)
        score = metric.measure(
            _test_case(
                snapshot={
                    "retrieved_courses": [
                        _course("Machine Learning with Python", "Machine Learning, Python Programming"),
                        _course("Cybersecurity Basics", "Network Security"),
                    ]
                },
                expected={"expected_skills": ["Machine Learning"]},
            )
        )

        self.assertEqual(score, 0.5)
        self.assertTrue(metric.is_successful())

    def test_hallucination_grounding_fails_unknown_course_title(self) -> None:
        metric = HallucinationGroundingMetric(threshold=1.0)
        score = metric.measure(
            _test_case(
                snapshot={
                    "retrieved_courses": [_course("Known Course", "Python Programming")],
                    "learning_path": {"stages": []},
                    "final_response": "- Imaginary Course (Unknown University)",
                },
                expected={},
            )
        )

        self.assertEqual(score, 0.0)
        self.assertFalse(metric.is_successful())

    def test_prerequisite_correctness_penalizes_warning(self) -> None:
        metric = PrerequisiteCorrectnessMetric(threshold=0.8)
        score = metric.measure(
            _test_case(
                snapshot={
                    "skill_gap_results": [{"missing_skills": ["Statistics"]}],
                    "guardrail_report": {
                        "issues": [
                            {
                                "check_name": "prerequisite_validation",
                                "severity": "warning",
                            }
                        ]
                    },
                },
                expected={},
            )
        )

        self.assertEqual(score, 0.9)
        self.assertTrue(metric.is_successful())

    def test_learning_path_quality_fails_oversized_path(self) -> None:
        metric = LearningPathQualityMetric(threshold=0.8)
        score = metric.measure(
            _test_case(
                snapshot={
                    "learning_path": {
                        "total_courses": 10,
                        "stages": [{"stage_number": 1, "courses": []}],
                    },
                    "guardrail_report": {"issues": []},
                },
                expected={"max_path_courses": 5},
            )
        )

        self.assertLess(score, 0.8)
        self.assertFalse(metric.is_successful())


def _test_case(snapshot: dict, expected: dict) -> LLMTestCase:
    return LLMTestCase(
        input="test query",
        actual_output=json.dumps(snapshot),
        expected_output=json.dumps(expected),
    )


def _course(title: str, skills_text: str) -> dict:
    return {
        "title": title,
        "organization": "Example University",
        "metadata": {"skills_text": skills_text},
    }


if __name__ == "__main__":
    unittest.main()
