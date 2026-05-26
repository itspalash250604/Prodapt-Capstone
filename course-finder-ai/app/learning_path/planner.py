"""Deterministic learning path planner."""

from __future__ import annotations

import json
import logging
import math
from collections.abc import Sequence
from time import perf_counter

from app.llm.service import deepseek_generate_structured
from app.learning_path.models import (
    LearningPath,
    LearningPathCourse,
    LearningPathRequest,
    LearningPathStage,
)
from app.retrieval.models import CourseSearchResult
from app.skill_gap.analyzer import SkillGapAnalyzer, parse_skills
from app.skill_gap.models import FoundationalCourseRecommendation, SkillGapResult


logger = logging.getLogger(__name__)


DIFFICULTY_ORDER = {
    "Beginner": 1,
    "Mixed": 2,
    "Intermediate": 3,
    "Advanced": 4,
}

COURSE_TYPE_PRIORITY = {
    "Professional Certificate": 1,
    "Specialization": 2,
    "Course": 3,
    "Guided Project": 4,
    "Project": 5,
}


class LearningPathPlanner:
    """Build a goal-aligned, prerequisite-aware course sequence."""

    def __init__(self, skill_gap_analyzer: SkillGapAnalyzer) -> None:
        self.skill_gap_analyzer = skill_gap_analyzer

    def plan(
        self,
        request: LearningPathRequest,
        ranked_candidates: Sequence[CourseSearchResult],
    ) -> LearningPath:
        started_at = perf_counter()
        if not request.learning_goal.strip():
            raise ValueError("learning_goal must not be empty")
        if request.max_courses <= 0:
            raise ValueError("max_courses must be greater than zero")
        if not ranked_candidates:
            result = self._empty_path(request)
            logger.info(
                "recommendations.learning_path.plan_complete total_ms=%.1f candidates=%s stages=%s",
                (perf_counter() - started_at) * 1000.0,
                0,
                0,
            )
            return result

        selected_candidates = self._filter_candidates(
            ranked_candidates,
            request.target_difficulty,
        )
        skill_gaps = [
            self.skill_gap_analyzer.analyze(request.student_profile, candidate)
            for candidate in selected_candidates[: request.candidate_k]
        ]

        seen_course_ids: set[str] = set()
        foundation_limit = self._foundation_slot_count(skill_gaps, request.max_courses)
        foundation_courses = self._foundation_courses(
            skill_gaps,
            seen_course_ids,
            limit=foundation_limit,
        )
        remaining_slots = max(request.max_courses - len(foundation_courses), 0)

        core_courses = self._goal_courses(
            selected_candidates,
            seen_course_ids,
            limit=remaining_slots,
        )

        stages = self._build_stages(foundation_courses, core_courses)
        readiness_summary = self._readiness_summary(skill_gaps)
        note = build_learning_path_note(request, stages, readiness_summary)
        result = LearningPath(
            goal=request.learning_goal,
            readiness_summary=readiness_summary,
            stages=stages,
            total_courses=sum(len(stage.courses) for stage in stages),
            note=note,
        )

        logger.info(
            "recommendations.learning_path.plan_complete total_ms=%.1f candidates=%s stages=%s",
            (perf_counter() - started_at) * 1000.0,
            len(ranked_candidates),
            len(stages),
        )
        return result

    @staticmethod
    def _filter_candidates(
        candidates: Sequence[CourseSearchResult],
        target_difficulty: str | None,
    ) -> list[CourseSearchResult]:
        if not target_difficulty:
            return list(candidates)
        target_rank = DIFFICULTY_ORDER.get(target_difficulty)
        if target_rank is None:
            return list(candidates)
        return [
            candidate
            for candidate in candidates
            if DIFFICULTY_ORDER.get(str(candidate.metadata.get("difficulty", "")), 99) <= target_rank
        ]

    @staticmethod
    def _foundation_courses(
        skill_gaps: list[SkillGapResult],
        seen_course_ids: set[str],
        limit: int,
    ) -> list[LearningPathCourse]:
        courses: list[LearningPathCourse] = []
        for gap in sorted(skill_gaps, key=lambda item: item.readiness_score):
            for recommendation in gap.foundational_courses:
                if len(courses) >= limit:
                    return courses
                if recommendation.course_id in seen_course_ids:
                    continue
                seen_course_ids.add(recommendation.course_id)
                courses.append(course_from_foundation(recommendation))
        return courses

    @staticmethod
    def _goal_courses(
        candidates: Sequence[CourseSearchResult],
        seen_course_ids: set[str],
        limit: int,
    ) -> list[LearningPathCourse]:
        sorted_candidates = sorted(
            candidates,
            key=lambda candidate: (
                -candidate.score,
                DIFFICULTY_ORDER.get(str(candidate.metadata.get("difficulty", "")), 99),
                COURSE_TYPE_PRIORITY.get(str(candidate.metadata.get("course_type", "")), 99),
            ),
        )

        courses: list[LearningPathCourse] = []
        for candidate in sorted_candidates:
            if len(courses) >= limit:
                break
            if candidate.course_id in seen_course_ids:
                continue
            seen_course_ids.add(candidate.course_id)
            courses.append(course_from_candidate(candidate))
        return courses

    @staticmethod
    def _build_stages(
        foundation_courses: list[LearningPathCourse],
        goal_courses: list[LearningPathCourse],
    ) -> list[LearningPathStage]:
        stages: list[LearningPathStage] = []
        stage_number = 1

        if foundation_courses:
            stages.append(
                LearningPathStage(
                    stage_number=stage_number,
                    title="Foundations",
                    purpose="Build missing preparation skills before deeper course work.",
                    courses=foundation_courses,
                )
            )
            stage_number += 1

        grouped_goal_courses = group_goal_courses(goal_courses)
        for title, purpose, courses in grouped_goal_courses:
            if not courses:
                continue
            stages.append(
                LearningPathStage(
                    stage_number=stage_number,
                    title=title,
                    purpose=purpose,
                    courses=courses,
                )
            )
            stage_number += 1

        return stages

    @staticmethod
    def _readiness_summary(skill_gaps: list[SkillGapResult]) -> str:
        if not skill_gaps:
            return "No candidate courses were available for readiness analysis."

        average_readiness = sum(gap.readiness_score for gap in skill_gaps) / len(skill_gaps)
        common_missing: list[str] = []
        for gap in skill_gaps:
            for skill in gap.missing_skills:
                if skill not in common_missing:
                    common_missing.append(skill)
            if len(common_missing) >= 5:
                break

        if common_missing:
            missing_text = ", ".join(common_missing)
            return (
                f"Average readiness across candidates is {average_readiness:.0%}. "
                f"Suggested preparation focus: {missing_text}."
            )
        return f"Average readiness across candidates is {average_readiness:.0%}. No major gaps found."

    @staticmethod
    def _foundation_slot_count(
        skill_gaps: list[SkillGapResult],
        max_courses: int,
    ) -> int:
        if max_courses <= 1 or not skill_gaps:
            return 0

        average_readiness = sum(gap.readiness_score for gap in skill_gaps) / len(skill_gaps)
        if average_readiness < 0.25:
            return min(max_courses - 1, max(2, math.ceil(max_courses * 0.6)))
        if average_readiness < 0.5:
            return min(max_courses - 1, max(2, math.ceil(max_courses * 0.5)))
        if average_readiness < 0.8:
            return min(max_courses - 1, max(1, math.ceil(max_courses * 0.35)))
        return min(max_courses - 1, 1)

    @staticmethod
    def _empty_path(request: LearningPathRequest) -> LearningPath:
        return LearningPath(
            goal=request.learning_goal,
            readiness_summary="No courses were available to build a learning path.",
            stages=[],
            total_courses=0,
            note="No path was generated because no candidate courses were provided.",
        )


def group_goal_courses(
    courses: list[LearningPathCourse],
) -> list[tuple[str, str, list[LearningPathCourse]]]:
    core: list[LearningPathCourse] = []
    applied: list[LearningPathCourse] = []
    advanced: list[LearningPathCourse] = []

    for course in courses:
        difficulty_rank = DIFFICULTY_ORDER.get(course.difficulty, 99)
        if course.course_type in {"Guided Project", "Project"}:
            applied.append(course)
        elif difficulty_rank >= DIFFICULTY_ORDER["Advanced"]:
            advanced.append(course)
        elif difficulty_rank >= DIFFICULTY_ORDER["Intermediate"] and len(core) >= 2:
            advanced.append(course)
        else:
            core.append(course)

    return [
        ("Core Learning", "Learn the main concepts and skills for the goal.", core),
        ("Applied Practice", "Practice the goal with hands-on or project-style courses.", applied),
        ("Advanced Growth", "Move into deeper specialization after core skills are covered.", advanced),
    ]


def course_from_candidate(candidate: CourseSearchResult) -> LearningPathCourse:
    metadata = candidate.metadata
    return LearningPathCourse(
        course_id=candidate.course_id,
        title=candidate.title,
        organization=candidate.organization,
        difficulty=str(metadata.get("difficulty", "")),
        course_type=str(metadata.get("course_type", "")),
        skills=parse_skills(str(metadata.get("skills_text", ""))),
        reason="Selected because it aligns with the learning goal and fits the path progression.",
        relevance_score=candidate.score,
    )


def build_learning_path_note(
    request: LearningPathRequest,
    stages: list[LearningPathStage],
    readiness_summary: str,
) -> str:
    started_at = perf_counter()
    system_prompt = (
        "You write concise learning path summaries for a course recommendation system. "
        "Keep the response grounded in the provided stages and return 2-4 short sentences."
    )
    stage_lines = []
    for stage in stages:
        course_titles = ", ".join(course.title for course in stage.courses) or "None"
        stage_lines.append(f"Stage {stage.stage_number} - {stage.title}: {course_titles}")

    user_prompt = (
        f"Learning goal: {request.learning_goal}\n"
        f"Target difficulty: {request.target_difficulty or 'None'}\n"
        f"Readiness summary: {readiness_summary}\n"
        f"Stages:\n{chr(10).join(stage_lines) if stage_lines else 'None'}\n\n"
        "Write a short explanation of how the path progresses from foundations to goal-aligned courses."
    )
    payload = deepseek_generate_structured(
        system_prompt,
        user_prompt,
        max_new_tokens=160,
        fallback_payload={
            "summary": (
                "Path is generated from dataset courses only. Stage order is based on "
                "difficulty progression, inferred preparation needs, and retrieval relevance."
            ),
            "readiness_summary": readiness_summary,
            "stage_count": len(stages),
        },
    )
    summary = str(payload.get("summary") or "Path is generated from dataset courses only.")
    readiness = str(payload.get("readiness_summary") or readiness_summary)
    stage_count = payload.get("stage_count", len(stages))
    logger.info(
        "recommendations.learning_path.note_complete total_ms=%.1f stages=%s",
        (perf_counter() - started_at) * 1000.0,
        len(stages),
    )
    return f"{summary} Readiness: {readiness} Stage count: {stage_count}."


def course_from_foundation(
    recommendation: FoundationalCourseRecommendation,
) -> LearningPathCourse:
    return LearningPathCourse(
        course_id=recommendation.course_id,
        title=recommendation.title,
        organization=recommendation.organization,
        difficulty="Beginner",
        course_type="Course",
        skills=[],
        reason=recommendation.reason,
        relevance_score=recommendation.score,
        missing_skill=recommendation.missing_skill,
    )
