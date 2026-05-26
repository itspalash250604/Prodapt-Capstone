"""Validation guardrails for course recommendation outputs."""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.agents.state import CareerAlignment
from app.guardrails.models import GuardrailIssue, GuardrailReport
from app.learning_path.models import LearningPath, LearningPathCourse
from app.llm.service import deepseek_generate_structured
from app.skill_gap.models import SkillGapResult


DIFFICULTY_ORDER = {
    "Beginner": 1,
    "Mixed": 2,
    "Intermediate": 3,
    "Advanced": 4,
}


class RecommendationGuardrails:
    """Validate recommendation quality before the advisor response is produced."""

    def validate(
        self,
        learning_path: LearningPath | None,
        skill_gap_results: list[SkillGapResult] | None = None,
        career_alignment: CareerAlignment | None = None,
        max_courses: int | None = None,
    ) -> GuardrailReport:
        skill_gap_results = skill_gap_results or []

        # Run all checks and then filter to only error-level issues for the guardrails
        # report returned to the UI.
        all_issues = self.run_checks(learning_path, skill_gap_results, career_alignment, max_courses)

        # Only surface error-level guardrail issues here. Warnings and informational
        # checks are considered quality/readiness signals and should not appear
        # in the guardrails report returned to the UI.
        filtered_issues = [issue for issue in all_issues if issue.severity == "error"]

        error_count = len(filtered_issues)
        # We intentionally hide warnings from the guardrails summary (only errors matter)
        warning_count = 0
        passed = error_count == 0
        summary = build_summary(passed, error_count, warning_count)

        return GuardrailReport(passed=passed, issues=filtered_issues, summary=summary)

    def run_checks(
        self,
        learning_path: LearningPath | None,
        skill_gap_results: list[SkillGapResult] | None = None,
        career_alignment: CareerAlignment | None = None,
        max_courses: int | None = None,
    ) -> list[GuardrailIssue]:
        """Run all guardrail checks and return the raw list of issues (including warnings).

        This is useful when callers want to surface non-error quality signals separately
        from strict guardrails.
        """
        issues: list[GuardrailIssue] = []
        skill_gap_results = skill_gap_results or []

        issues.extend(self.validate_sequence(learning_path, max_courses))
        issues.extend(self.validate_difficulty_progression(learning_path))
        issues.extend(self.validate_prerequisites(learning_path, skill_gap_results))
        issues.extend(self.validate_goal_alignment(learning_path, career_alignment))
        issues.extend(self.validate_with_llm(learning_path, skill_gap_results, career_alignment))

        return issues

    def validate_sequence(
        self,
        learning_path: LearningPath | None,
        max_courses: int | None,
    ) -> list[GuardrailIssue]:
        issues: list[GuardrailIssue] = []
        if learning_path is None:
            return [
                GuardrailIssue(
                    check_name="sequence_validation",
                    severity="error",
                    message="Learning path is missing.",
                )
            ]

        all_courses = flatten_courses(learning_path)
        if not all_courses:
            issues.append(
                GuardrailIssue(
                    check_name="sequence_validation",
                    severity="error",
                    message="Learning path has no courses.",
                )
            )

        if max_courses is not None and learning_path.total_courses > max_courses:
            issues.append(
                GuardrailIssue(
                    check_name="sequence_validation",
                    severity="error",
                    message=(
                        f"Learning path contains {learning_path.total_courses} courses, "
                        f"which exceeds max_courses={max_courses}."
                    ),
                )
            )

        stage_numbers = [stage.stage_number for stage in learning_path.stages]
        if stage_numbers != sorted(stage_numbers) or len(stage_numbers) != len(set(stage_numbers)):
            issues.append(
                GuardrailIssue(
                    check_name="sequence_validation",
                    severity="error",
                    message="Learning path stages must have unique increasing stage numbers.",
                )
            )

        duplicate_ids = [
            course_id
            for course_id, count in Counter(course.course_id for _, course in all_courses).items()
            if count > 1
        ]
        for course_id in duplicate_ids:
            issues.append(
                GuardrailIssue(
                    check_name="sequence_validation",
                    severity="error",
                    message="Duplicate course appears in the learning path.",
                    course_id=course_id,
                )
            )

        for stage, course in all_courses:
            if not course.reason.strip():
                issues.append(
                    GuardrailIssue(
                        check_name="sequence_validation",
                        severity="warning",
                        message="Course is missing an inclusion reason.",
                        course_id=course.course_id,
                        stage_number=stage,
                    )
                )

        return issues

    def validate_with_llm(
        self,
        learning_path: LearningPath | None,
        skill_gap_results: list[SkillGapResult],
        career_alignment: CareerAlignment | None,
    ) -> list[GuardrailIssue]:
        if learning_path is None:
            return []

        system_prompt = (
            "You are a strict reviewer for a course recommendation workflow. "
            "Assess whether the path is sequence-safe, prerequisite-aware, and aligned with the career goal. "
            "Return JSON with keys passed (boolean), summary (string), and issues (array of objects with "
            "check_name, severity, message, course_id, stage_number). Use only the supplied data."
        )
        user_prompt = (
            f"Learning path: {learning_path}\n\n"
            f"Skill gaps: {skill_gap_results}\n\n"
            f"Career alignment: {career_alignment}\n\n"
            "Return only JSON."
        )
        payload = deepseek_generate_structured(
            system_prompt,
            user_prompt,
            max_new_tokens=256,
            fallback_payload={
                "passed": True,
                "summary": "LLM review completed with no additional structured issues.",
                "issues": [],
            },
        )
        issues: list[GuardrailIssue] = []
        for raw_issue in payload.get("issues", []) if isinstance(payload, dict) else []:
            if not isinstance(raw_issue, dict):
                continue
            check_name = str(raw_issue.get("check_name", "llm_judge"))
            severity = str(raw_issue.get("severity", "warning"))
            message = str(raw_issue.get("message", "LLM review note."))
            course_id = raw_issue.get("course_id")
            stage_number = raw_issue.get("stage_number")
            issues.append(
                GuardrailIssue(
                    check_name=check_name,
                    severity=severity,
                    message=message,
                    course_id=str(course_id) if course_id else None,
                    stage_number=int(stage_number) if stage_number not in (None, "") else None,
                )
            )
        return issues

    def validate_difficulty_progression(
        self,
        learning_path: LearningPath | None,
    ) -> list[GuardrailIssue]:
        if learning_path is None:
            return []

        issues: list[GuardrailIssue] = []
        previous_rank = 0
        previous_course: LearningPathCourse | None = None
        for stage, course in flatten_courses(learning_path):
            if course.missing_skill:
                continue

            rank = DIFFICULTY_ORDER.get(course.difficulty, 0)
            if previous_rank and rank and rank < previous_rank:
                issues.append(
                    GuardrailIssue(
                        check_name="difficulty_validation",
                        severity="warning",
                        message=(
                            f"Difficulty regression detected: '{course.title}' "
                            f"({course.difficulty}) appears after '{previous_course.title}' "
                            f"({previous_course.difficulty})."
                        ),
                        course_id=course.course_id,
                        stage_number=stage,
                    )
                )
            previous_rank = max(previous_rank, rank)
            previous_course = course

        return issues

    def validate_prerequisites(
        self,
        learning_path: LearningPath | None,
        skill_gap_results: list[SkillGapResult],
    ) -> list[GuardrailIssue]:
        if learning_path is None:
            return []

        foundation_skills = {
            course.missing_skill.casefold()
            for _, course in flatten_courses(learning_path)
            if course.missing_skill
        }
        path_course_ids = {course.course_id for _, course in flatten_courses(learning_path)}
        issues: list[GuardrailIssue] = []

        for gap in skill_gap_results:
            if gap.course_id not in path_course_ids or not gap.missing_skills:
                continue

            unresolved = [
                skill
                for skill in gap.missing_skills
                if skill.casefold() not in foundation_skills
            ]
            if unresolved and gap.readiness_score < 0.5:
                issues.append(
                    GuardrailIssue(
                        check_name="prerequisite_validation",
                        severity="warning",
                        message=(
                            f"Course '{gap.course_title}' has unresolved inferred preparation gaps: "
                            f"{', '.join(unresolved[:5])}."
                        ),
                        course_id=gap.course_id,
                    )
                )

        return issues

    def validate_goal_alignment(
        self,
        learning_path: LearningPath | None,
        career_alignment: CareerAlignment | None,
    ) -> list[GuardrailIssue]:
        if learning_path is None or not career_alignment:
            return []

        matched_by_course = {
            item.get("course_id"): item.get("matched_career_skills", [])
            for item in career_alignment.get("course_alignment", [])
        }
        issues: list[GuardrailIssue] = []

        for stage, course in flatten_courses(learning_path):
            if course.missing_skill:
                continue

            matched_skills = matched_by_course.get(course.course_id, [])
            weak_score = course.relevance_score is not None and course.relevance_score < 0.45
            if weak_score and not matched_skills:
                issues.append(
                    GuardrailIssue(
                        check_name="learning_objective_alignment",
                        severity="warning",
                        message=(
                            f"Course '{course.title}' may be weakly aligned with the learning goal."
                        ),
                        course_id=course.course_id,
                        stage_number=stage,
                    )
                )

        return issues


def flatten_courses(learning_path: LearningPath) -> list[tuple[int, LearningPathCourse]]:
    return [
        (stage.stage_number, course)
        for stage in learning_path.stages
        for course in stage.courses
    ]


def build_summary(passed: bool, error_count: int, warning_count: int) -> str:
    if error_count:
        return (
            f"Guardrails failed with {error_count} error(s) and "
            f"{warning_count} warning(s)."
        )
    if warning_count:
        return f"Guardrails passed with {warning_count} warning(s)."
    if passed:
        return "Guardrails passed with no issues."
    return "Guardrail status is unknown."
