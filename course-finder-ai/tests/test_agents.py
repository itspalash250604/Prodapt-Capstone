"""Lightweight tests for recommendation graph agents."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.agents.advisor_agent import learning_advisor_agent
from app.agents.career_alignment_agent import career_alignment_agent
from app.agents.graph import build_recommendation_graph
from app.retrieval.models import CourseSearchResult
from app.skill_gap.models import StudentProfile


class AgentTest(unittest.TestCase):
    def test_career_alignment_agent_maps_known_goal(self) -> None:
        state = {
            "query": "machine learning engineer",
            "student_profile": StudentProfile(current_skills=["Python"]),
            "career_goal": "machine learning engineer",
            "retrieved_courses": [
                _course(
                    "course-1",
                    "Machine Learning",
                    "Machine Learning, Python Programming, Cloud Computing",
                )
            ],
        }

        result = career_alignment_agent(state)

        self.assertIn("career_alignment", result)
        self.assertIn("Machine Learning", result["career_alignment"]["matched_skill_clusters"])
        self.assertEqual(
            result["career_alignment"]["course_alignment"][0]["matched_career_skills"],
            ["Python Programming", "Machine Learning", "Cloud Computing"],
        )

    def test_career_alignment_score_increases_with_more_skill_overlap(self) -> None:
        base_state = {
            "query": "machine learning engineer",
            "student_profile": StudentProfile(current_skills=["Python"]),
            "career_goal": "machine learning engineer",
            "retrieved_courses": [
                _course(
                    "course-1",
                    "Machine Learning",
                    "Machine Learning, Python Programming, Cloud Computing",
                )
            ],
        }

        richer_state = {
            **base_state,
            "student_profile": StudentProfile(
                current_skills=["Python", "Machine Learning", "Cloud Computing", "Deep Learning"]
            ),
        }

        base_result = career_alignment_agent(base_state)
        richer_result = career_alignment_agent(richer_state)

        self.assertIn("alignment_score", base_result["career_alignment"])
        self.assertIn("score_breakdown", base_result["career_alignment"])
        self.assertGreater(richer_result["career_alignment"]["alignment_score"], base_result["career_alignment"]["alignment_score"])
        self.assertGreater(richer_result["career_alignment"]["alignment_score"], 0)

    def test_career_alignment_score_changes_with_llm_refinement(self) -> None:
        state = {
            "query": "machine learning engineer",
            "student_profile": StudentProfile(current_skills=["Python", "Machine Learning"]),
            "career_goal": "machine learning engineer",
            "retrieved_courses": [
                _course(
                    "course-1",
                    "Machine Learning",
                    "Machine Learning, Python Programming, Cloud Computing",
                )
            ],
        }

        score_calls = {"count": 0}

        def fake_qwen(system_prompt: str, user_prompt: str, **kwargs):
            if "Deterministic base score" in user_prompt:
                score_calls["count"] += 1
                if score_calls["count"] == 1:
                    return {"final_score": 0.95, "adjustment": 0.05, "confidence": 0.9, "rationale": "High fit"}
                return {"final_score": 0.25, "adjustment": -0.3, "confidence": 0.9, "rationale": "Lower fit"}

            return {
                "summary": "LLM summary",
                "career_goal": "machine learning engineer",
                "matched_skill_count": 3,
                "alignment_score": 0.5,
                "confidence": 0.9,
            }

        with patch("app.agents.career_alignment_agent.qwen_generate_structured", side_effect=fake_qwen):
            high_result = career_alignment_agent(state)
            low_result = career_alignment_agent(state)

        self.assertGreater(high_result["career_alignment"]["alignment_score"], low_result["career_alignment"]["alignment_score"])
        self.assertGreaterEqual(high_result["career_alignment"]["alignment_score"], 0)
        self.assertLessEqual(low_result["career_alignment"]["alignment_score"], 1)
        self.assertIn("llm_score", high_result["career_alignment"]["score_breakdown"])
        self.assertIn("rationale", high_result["career_alignment"]["score_breakdown"])

    def test_advisor_agent_creates_final_response(self) -> None:
        state = {
            "query": "data science",
            "retrieved_courses": [_course("course-1", "Python for Data Science", "Python Programming")],
        }

        result = learning_advisor_agent(state)

        self.assertIn("final_response", result)
        self.assertIn("Python for Data Science", result["final_response"])

    def test_advisor_agent_enriches_courses_with_llm(self) -> None:
        state = {
            "query": "data science",
            "retrieved_courses": [_course("course-1", "Python for Data Science", "Python Programming")],
        }

        def fake_enrich(system_prompt: str, user_prompt: str, **kwargs):
            return {
                "description": "A hands-on intro to Python for data analysis.",
                "rationale": "Covers core Python data libraries and is suitable for learners with this profile.",
                "time_to_complete": "12 hours",
                "match_percentage": 0.92,
            }

        with patch("app.agents.advisor_agent.qwen_generate_structured", side_effect=fake_enrich):
            from app.agents.advisor_agent import build_final_payload

            payload = build_final_payload(state)
            recs = payload.get("recommendations", [])
            self.assertTrue(len(recs) > 0)
            first = recs[0]
            self.assertIn("description", first)
            self.assertIn("rationale", first)
            self.assertIn("time_to_complete", first)
            self.assertIn("match_percentage", first)
            self.assertEqual(first["match_percentage"], 0.92)

    def test_graph_compiles(self) -> None:
        graph = build_recommendation_graph()

        self.assertIsNotNone(graph)


def _course(course_id: str, title: str, skills_text: str) -> CourseSearchResult:
    return CourseSearchResult(
        course_id=course_id,
        title=title,
        organization="Example University",
        score=0.9,
        metadata={
            "difficulty": "Beginner",
            "course_type": "Course",
            "skills_text": skills_text,
        },
        document="Course text",
    )


if __name__ == "__main__":
    unittest.main()
