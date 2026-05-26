"""Integration test for explicit Qwen and DeepSeek routing."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from app.agents.graph import build_recommendation_graph
from app.retrieval.models import CourseSearchResult
from app.skill_gap.models import StudentProfile


class ModelRoutingIntegrationTest(unittest.TestCase):
    def test_graph_uses_qwen_for_narrative_steps_and_deepseek_for_analysis_steps(self) -> None:
        graph = build_recommendation_graph()
        retrieved_courses = [
            _course("ml-1", "Machine Learning Foundations", "Beginner", 0.97, "Machine Learning, Python Programming"),
            _course("ml-2", "Applied Machine Learning", "Intermediate", 0.94, "Machine Learning, Data Analysis"),
        ]
        foundation_courses = [
            _course("foundation-1", "Statistics Basics", "Beginner", 0.88, "General Statistics, Spreadsheet Software"),
        ]

        with (
            patch("app.agents.course_retrieval_agent.SemanticCourseRetriever") as retrieval_retriever_cls,
            patch("app.agents.course_retrieval_agent.CrossEncoderCourseReranker") as reranker_cls,
            patch("app.agents.course_retrieval_agent.qwen_generate_structured") as qwen_rewrite,
            patch("app.skill_gap.analyzer.deepseek_generate_structured") as deepseek_skill,
            patch("app.agents.skill_gap_agent.SemanticCourseRetriever") as skill_retriever_cls,
            patch("app.learning_path.planner.deepseek_generate_structured") as deepseek_path,
            patch("app.agents.learning_path_agent.SemanticCourseRetriever") as planning_retriever_cls,
            patch("app.agents.career_alignment_agent.qwen_generate_structured") as qwen_career,
            patch("app.guardrails.validators.deepseek_generate_structured") as deepseek_guardrails,
            patch("app.agents.advisor_agent.qwen_generate_structured") as qwen_advisor,
        ):
            retrieval_retriever = retrieval_retriever_cls.return_value
            retrieval_retriever.search.return_value = retrieved_courses

            reranker = reranker_cls.return_value
            reranker.rerank.side_effect = lambda query, candidates, top_k=None: list(candidates)[:top_k]

            skill_retriever = skill_retriever_cls.return_value
            skill_retriever.search.return_value = foundation_courses

            planning_retriever = planning_retriever_cls.return_value
            planning_retriever.search.return_value = foundation_courses

            qwen_rewrite.side_effect = lambda *args, **kwargs: {
                "rewritten_query": "machine learning engineer",
                "intent_summary": "machine learning engineer upskilling",
            }
            deepseek_skill.side_effect = lambda *args, **kwargs: {
                "summary": "DeepSeek skill-gap summary",
                "readiness_score": 0.5,
                "missing_skills": ["General Statistics"],
            }
            deepseek_path.side_effect = lambda *args, **kwargs: {
                "summary": "DeepSeek learning-path summary",
                "readiness_summary": "Average readiness across candidates is 50%.",
                "stage_count": 2,
            }
            qwen_career.side_effect = lambda *args, **kwargs: {
                "summary": "Qwen career alignment summary",
                "career_goal": "machine learning engineer",
                "matched_skill_count": 3,
            }
            deepseek_guardrails.side_effect = lambda *args, **kwargs: {
                "passed": True,
                "summary": "DeepSeek guardrail review passed",
                "issues": [],
            }
            qwen_advisor.side_effect = lambda *args, **kwargs: {
                "query": "machine learning engineer",
                "recommendations": [
                    {
                        "rank": 1,
                        "course_id": "ml-1",
                        "title": "Machine Learning Foundations",
                        "organization": "Example University",
                        "difficulty": "Beginner",
                        "course_type": "Course",
                        "score": 0.97,
                    }
                ],
                "readiness": [],
                "learning_path": {"goal": "machine learning engineer", "stages": []},
                "career_alignment": {"summary": "Qwen career alignment summary"},
                "guardrails": {"passed": True, "issues": []},
                "note": "Qwen final response summary",
            }

            final_state = graph.invoke(
                {
                    "query": "machine learning engineer",
                    "student_profile": StudentProfile(
                        current_skills=["Python"],
                        learning_goal="machine learning engineer",
                        career_goal="machine learning engineer",
                    ),
                    "career_goal": "machine learning engineer",
                    "candidate_k": 2,
                    "top_k": 2,
                    "max_path_courses": 3,
                    "use_reranker": True,
                }
            )

        self.assertGreater(qwen_rewrite.call_count, 0)
        self.assertGreater(deepseek_skill.call_count, 0)
        self.assertGreater(deepseek_path.call_count, 0)
        self.assertGreater(qwen_career.call_count, 0)
        self.assertGreater(deepseek_guardrails.call_count, 0)
        self.assertGreater(qwen_advisor.call_count, 0)

        final_response = final_state["final_response"]
        self.assertIn("---STRUCTURED_PARAGRAPH---", final_response)
        self.assertIn("---CONDENSED---", final_response)
        self.assertIn("machine learning engineer", final_response)
        self.assertIn("Qwen career alignment summary", json.dumps(final_state["career_alignment"]))


def _course(course_id: str, title: str, difficulty: str, score: float, skills_text: str) -> CourseSearchResult:
    return CourseSearchResult(
        course_id=course_id,
        title=title,
        organization="Example University",
        score=score,
        metadata={
            "difficulty": difficulty,
            "course_type": "Course",
            "skills_text": skills_text,
        },
        document="Course text",
    )


if __name__ == "__main__":
    unittest.main()