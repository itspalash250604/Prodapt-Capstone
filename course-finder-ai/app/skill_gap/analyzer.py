"""Deterministic prerequisite and missing skill detection."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterable
from time import perf_counter
from typing import Protocol

from app.llm.service import deepseek_generate_structured
from app.retrieval.models import CourseSearchResult
from app.skill_gap.models import (
    CourseCandidate,
    FoundationalCourseRecommendation,
    SkillGapResult,
    StudentProfile,
)


logger = logging.getLogger(__name__)


class CourseRetriever(Protocol):
    """Retriever interface used for foundational course recommendations."""

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: dict[str, object] | None = None,
    ) -> list[CourseSearchResult]:
        ...


SKILL_ALIASES = {
    "ai": "Artificial Intelligence",
    "artificial intelligence": "Artificial Intelligence",
    "cloud": "Cloud Computing",
    "cloud computing": "Cloud Computing",
    "cyber security": "Cybersecurity",
    "cybersecurity": "Cybersecurity",
    "data analytics": "Data Analysis",
    "data analysis": "Data Analysis",
    "data science": "Data Science",
    "deep learning": "Deep Learning",
    "excel": "Microsoft Excel",
    "gen ai": "Generative AI",
    "generative ai": "Generative AI",
    "machine learning": "Machine Learning",
    "ml": "Machine Learning",
    "networking": "Computer Networking",
    "networks": "Computer Networking",
    "numpy": "NumPy",
    "pandas": "Pandas",
    "project management": "Project Management",
    "python": "Python Programming",
    "python programming": "Python Programming",
    "sql": "SQL",
    "statistics": "General Statistics",
    "stats": "General Statistics",
}

PREREQUISITE_SKILL_MAP = {
    "Artificial Intelligence": ["Python Programming", "Data Analysis"],
    "Big Data": ["Data Analysis", "Databases", "SQL"],
    "Cloud Applications": ["Cloud Computing", "Computer Networking"],
    "Cloud Computing": ["Computer Networking", "Operating Systems"],
    "Cloud Infrastructure": ["Cloud Computing", "Computer Networking"],
    "Computer Security Incident Management": ["Network Security", "System Security"],
    "Cyberattacks": ["Network Security", "System Security"],
    "Cybersecurity": ["Network Security", "Operating Systems"],
    "Data Analysis": ["General Statistics", "Spreadsheet Software"],
    "Data Engineering": ["Python Programming", "SQL", "Databases"],
    "Data Management": ["Databases", "SQL"],
    "Data Science": ["Python Programming", "Data Analysis", "General Statistics"],
    "Data Visualization": ["Data Analysis"],
    "Databases": ["SQL"],
    "Deep Learning": ["Machine Learning", "Python Programming", "Linear Algebra"],
    "DevOps": ["Cloud Computing", "Operating Systems"],
    "Generative AI": ["Artificial Intelligence", "Prompt Engineering"],
    "Machine Learning": ["Python Programming", "Data Analysis", "General Statistics"],
    "Natural Language Processing": ["Machine Learning", "Python Programming"],
    "Network Security": ["Computer Networking", "System Security"],
    "Python Programming": ["Computer Programming"],
    "Regression": ["General Statistics", "Data Analysis"],
    "Statistical Programming": ["General Statistics", "Python Programming"],
}

DIFFICULTY_LIMITS = {
    "Beginner": 3,
    "Mixed": 5,
    "Intermediate": 7,
    "Advanced": 10,
}


class SkillGapAnalyzer:
    """Analyze whether a student is ready for a target course."""

    def __init__(
        self,
        foundational_retriever: CourseRetriever | None = None,
        foundational_top_k_per_skill: int = 2,
    ) -> None:
        self.foundational_retriever = foundational_retriever
        self.foundational_top_k_per_skill = foundational_top_k_per_skill

    def analyze(
        self,
        student_profile: StudentProfile,
        course: CourseSearchResult | CourseCandidate,
    ) -> SkillGapResult:
        started_at = perf_counter()
        candidate = self._to_candidate(course)
        student_skills = canonical_skill_set(student_profile.current_skills)
        prerequisites = self.infer_prerequisites(candidate)
        prerequisite_keys = {normalize_skill(skill) for skill in prerequisites}

        matched = [
            skill
            for skill in prerequisites
            if normalize_skill(skill) in student_skills
        ]
        missing = [
            skill
            for skill in prerequisites
            if normalize_skill(skill) not in student_skills
        ]
        readiness_score = calculate_readiness_score(matched, prerequisites)
        note = build_skill_gap_note(candidate, student_profile, prerequisites, matched, missing, readiness_score)

        result = SkillGapResult(
            course_id=candidate.course_id,
            course_title=candidate.title,
            course_difficulty=candidate.difficulty,
            inferred_prerequisites=prerequisites,
            matched_skills=matched,
            missing_skills=missing,
            readiness_score=readiness_score,
            readiness_label=readiness_label(readiness_score, bool(prerequisite_keys)),
            foundational_courses=self.recommend_foundational_courses(missing, candidate.course_id),
            note=note,
        )

        logger.info(
            "recommendations.skill_gap.analyze_complete total_ms=%.1f course_id=%s missing_skills=%s",
            (perf_counter() - started_at) * 1000.0,
            candidate.course_id,
            len(missing),
        )
        return result

    def infer_prerequisites(self, course: CourseCandidate) -> list[str]:
        course_skills = parse_skills(course.skills_text)
        inferred: list[str] = []

        for skill in course_skills:
            normalized_course_skill = canonical_skill(skill)
            for prerequisite in PREREQUISITE_SKILL_MAP.get(normalized_course_skill, []):
                append_unique(inferred, prerequisite)

        difficulty = course.difficulty or "Mixed"
        max_prerequisites = DIFFICULTY_LIMITS.get(difficulty, 5)

        if difficulty == "Beginner":
            return inferred[:max_prerequisites]

        for skill in course_skills:
            canonical = canonical_skill(skill)
            if canonical in {
                "Python Programming",
                "SQL",
                "Data Analysis",
                "General Statistics",
                "Computer Networking",
                "Computer Programming",
            }:
                append_unique(inferred, canonical)

        return inferred[:max_prerequisites]

    def recommend_foundational_courses(
        self,
        missing_skills: list[str],
        target_course_id: str,
    ) -> list[FoundationalCourseRecommendation]:
        if self.foundational_retriever is None or not missing_skills:
            return []

        recommendations: list[FoundationalCourseRecommendation] = []
        seen_course_ids = {target_course_id}

        for skill in missing_skills:
            results = self.foundational_retriever.search(
                query=f"beginner course to learn {skill}",
                top_k=self.foundational_top_k_per_skill + 3,
                filters={"difficulty": "Beginner"},
            )
            for result in results:
                if result.course_id in seen_course_ids:
                    continue

                seen_course_ids.add(result.course_id)
                recommendations.append(
                    FoundationalCourseRecommendation(
                        missing_skill=skill,
                        course_id=result.course_id,
                        title=result.title,
                        organization=result.organization,
                        score=result.score,
                        reason=f"Recommended because it can help build preparation in {skill}.",
                    )
                )
                if count_recommendations_for_skill(recommendations, skill) >= self.foundational_top_k_per_skill:
                    break

        return recommendations

    @staticmethod
    def _to_candidate(course: CourseSearchResult | CourseCandidate) -> CourseCandidate:
        if isinstance(course, CourseCandidate):
            return course
        return CourseCandidate.from_search_result(course)


def parse_skills(skills_text: str) -> list[str]:
    return [
        skill.strip()
        for skill in re.split(r"[,|]", skills_text or "")
        if skill.strip()
    ]


def normalize_skill(skill: str) -> str:
    text = re.sub(r"[^a-z0-9+#. ]+", " ", skill.casefold())
    text = re.sub(r"\s+", " ", text).strip()
    return canonical_skill(text).casefold()


def canonical_skill(skill: str) -> str:
    key = re.sub(r"[^a-z0-9+#. ]+", " ", skill.casefold())
    key = re.sub(r"\s+", " ", key).strip()
    return SKILL_ALIASES.get(key, skill.strip())


def canonical_skill_set(skills: Iterable[str]) -> set[str]:
    return {normalize_skill(skill) for skill in skills if skill and skill.strip()}


def append_unique(values: list[str], value: str) -> None:
    if normalize_skill(value) not in {normalize_skill(existing) for existing in values}:
        values.append(value)


def calculate_readiness_score(matched: list[str], prerequisites: list[str]) -> float:
    if not prerequisites:
        return 1.0
    return round(len(matched) / len(prerequisites), 2)


def readiness_label(score: float, has_prerequisites: bool) -> str:
    if not has_prerequisites:
        return "ready"
    if score >= 0.8:
        return "ready"
    if score >= 0.5:
        return "mostly_ready"
    if score >= 0.25:
        return "needs_preparation"
    return "start_with_foundations"


def build_skill_gap_note(
    course: CourseCandidate,
    student_profile: StudentProfile,
    prerequisites: list[str],
    matched: list[str],
    missing: list[str],
    readiness_score: float,
) -> str:
    started_at = perf_counter()
    system_prompt = (
        "You write concise skill gap analysis notes for a course recommendation system. "
        "Keep the response grounded in the provided data and return 2-4 short sentences."
    )
    user_prompt = (
        f"Course: {course.title} ({course.organization})\n"
        f"Difficulty: {course.difficulty}\n"
        f"Student skills: {', '.join(student_profile.current_skills) if student_profile.current_skills else 'None'}\n"
        f"Inferred prerequisites: {', '.join(prerequisites) if prerequisites else 'None'}\n"
        f"Matched skills: {', '.join(matched) if matched else 'None'}\n"
        f"Missing skills: {', '.join(missing) if missing else 'None'}\n"
        f"Readiness score: {readiness_score:.0%}\n\n"
        "Write a short, user-friendly explanation of the gap and how to prepare."
    )
    payload = deepseek_generate_structured(
        system_prompt,
        user_prompt,
        max_new_tokens=160,
        fallback_payload={
            "summary": (
                "Prerequisites are inferred from course skills and difficulty. "
                "They are preparation guidance, not official Coursera requirements."
            ),
            "readiness_score": readiness_score,
            "missing_skills": missing,
        },
    )
    logger.info(
        "recommendations.skill_gap.note_complete total_ms=%.1f course_id=%s",
        (perf_counter() - started_at) * 1000.0,
        course.course_id,
    )
    return json.dumps(payload, ensure_ascii=False)


def count_recommendations_for_skill(
    recommendations: list[FoundationalCourseRecommendation],
    skill: str,
) -> int:
    return sum(1 for recommendation in recommendations if recommendation.missing_skill == skill)
