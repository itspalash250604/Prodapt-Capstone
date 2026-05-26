"""Evaluation runner for recommendation quality."""

from __future__ import annotations

import json

from deepeval.test_case import LLMTestCase

from app.agents.graph import build_recommendation_graph
from app.evaluation.metrics import (
    HallucinationGroundingMetric,
    LearningPathQualityMetric,
    PrerequisiteCorrectnessMetric,
    RecommendationRelevanceMetric,
)
from app.evaluation.models import EvaluationCase, EvaluationReport, MetricScore
from app.evaluation.serialization import recommendation_state_snapshot
from app.skill_gap.models import StudentProfile


DEFAULT_METRICS = [
    RecommendationRelevanceMetric(threshold=0.4),
    HallucinationGroundingMetric(threshold=1.0),
    PrerequisiteCorrectnessMetric(threshold=0.7),
    LearningPathQualityMetric(threshold=0.8),
]


def run_evaluation_case(case: EvaluationCase) -> EvaluationReport:
    graph = build_recommendation_graph()
    state = graph.invoke(
        {
            "query": case.query,
            "student_profile": StudentProfile(
                current_skills=case.current_skills,
                learning_goal=case.query,
                career_goal=case.career_goal or case.query,
            ),
            "career_goal": case.career_goal or case.query,
            "candidate_k": case.candidate_k,
            "top_k": case.top_k,
            "max_path_courses": case.max_path_courses,
            "use_reranker": case.use_reranker,
        }
    )
    snapshot = recommendation_state_snapshot(state)
    expected = {
        "expected_skills": case.expected_skills,
        "expected_course_keywords": case.expected_course_keywords,
        "max_path_courses": case.max_path_courses,
    }
    test_case = LLMTestCase(
        input=case.query,
        actual_output=json.dumps(snapshot),
        expected_output=json.dumps(expected),
    )

    metric_scores: list[MetricScore] = []
    for metric in DEFAULT_METRICS:
        score = metric.measure(test_case)
        metric_scores.append(
            MetricScore(
                name=metric.__name__,
                score=score,
                success=metric.is_successful(),
                reason=metric.reason,
            )
        )

    return EvaluationReport(
        case_name=case.name,
        query=case.query,
        metric_scores=metric_scores,
        passed=all(score.success for score in metric_scores),
        snapshot=snapshot,
    )


def default_evaluation_cases() -> list[EvaluationCase]:
    return [
        EvaluationCase(
            name="machine_learning_engineer",
            query="machine learning engineer",
            current_skills=["Python", "Data Analysis"],
            career_goal="machine learning engineer",
            expected_skills=["Machine Learning", "Python Programming", "Cloud Computing"],
            expected_course_keywords=["machine learning", "MLOps"],
            max_path_courses=6,
            use_reranker=False,
        ),
        EvaluationCase(
            name="cybersecurity_analyst",
            query="cybersecurity analyst",
            current_skills=["Computer Networking"],
            career_goal="cybersecurity analyst",
            expected_skills=["Network Security", "System Security", "Cyberattacks"],
            expected_course_keywords=["cybersecurity", "security analyst"],
            max_path_courses=5,
            use_reranker=False,
        ),
    ]
