"""Career Alignment Agent."""

from __future__ import annotations

import json
import logging
from time import perf_counter

from app.agents.state import CareerAlignment, RecommendationState
from app.llm.service import qwen_generate_structured
from app.skill_gap.analyzer import parse_skills


logger = logging.getLogger(__name__)


CAREER_SKILL_CLUSTERS = {
    "data scientist": ["Python Programming", "SQL", "General Statistics", "Machine Learning", "Data Visualization"],
    "machine learning engineer": ["Python Programming", "Machine Learning", "Deep Learning", "MLOps", "Cloud Computing"],
    "cybersecurity analyst": ["Network Security", "System Security", "Cyberattacks", "Operating Systems"],
    "cloud engineer": ["Cloud Computing", "Cloud Infrastructure", "Computer Networking", "DevOps"],
    "project manager": ["Project Management", "Communication", "Leadership and Management", "Strategy"],
    "business analyst": ["Business Analysis", "Data Analysis", "Communication", "Microsoft Excel"],
}


def career_alignment_agent(state: RecommendationState) -> RecommendationState:
    """Map recommended courses to the user's career goal."""
    started_at = perf_counter()
    career_goal = state.get("career_goal") or state["query"]
    target_skills = infer_career_skills(career_goal)
    student_profile = state.get("student_profile")
    current_skills = list(getattr(student_profile, "current_skills", []) or [])
    course_alignment = []

    for course in state.get("retrieved_courses", [])[:5]:
        course_skills = parse_skills(str(course.metadata.get("skills_text", "")))
        matched = [
            skill
            for skill in target_skills
            if skill.casefold() in {course_skill.casefold() for course_skill in course_skills}
        ]
        course_alignment.append(
            {
                "course_id": course.course_id,
                "title": course.title,
                "matched_career_skills": matched,
            }
        )

    score_details = calculate_alignment_score(target_skills, course_alignment, current_skills)
    alignment_score = score_details["final_score"]
    summary = build_summary(career_goal, target_skills, course_alignment, current_skills, alignment_score, score_details)
    alignment: CareerAlignment = {
        "career_goal": career_goal,
        "matched_skill_clusters": target_skills,
        "course_alignment": course_alignment,
        "alignment_score": alignment_score,
        "score": alignment_score,
        "score_breakdown": score_details,
        "summary": summary,
    }

    logger.info(
        "recommendations.career_alignment.complete total_ms=%.1f courses=%s target_skills=%s",
        (perf_counter() - started_at) * 1000.0,
        len(course_alignment),
        len(target_skills),
    )

    return {
        **state,
        "career_alignment": alignment,
    }


def infer_career_skills(career_goal: str) -> list[str]:
    goal = career_goal.casefold()
    for career, skills in CAREER_SKILL_CLUSTERS.items():
        if career in goal:
            return skills

    if "machine learning" in goal or "ml" in goal:
        return CAREER_SKILL_CLUSTERS["machine learning engineer"]
    if "cyber" in goal or "security" in goal:
        return CAREER_SKILL_CLUSTERS["cybersecurity analyst"]
    if "cloud" in goal or "devops" in goal:
        return CAREER_SKILL_CLUSTERS["cloud engineer"]
    if "data" in goal:
        return CAREER_SKILL_CLUSTERS["data scientist"]

    return ["Communication", "Problem Solving", "Critical Thinking"]


def build_summary(
    career_goal: str,
    target_skills: list[str],
    course_alignment: list[dict],
    current_skills: list[str],
    alignment_score: float,
    score_details: dict[str, float | str],
) -> str:
    summary_started_at = perf_counter()
    system_prompt = (
        "You write concise career alignment summaries for a course recommendation system. "
        "Keep the response grounded in the provided course-to-skill matches and return 2-4 sentences. "
        "Return JSON with summary, career_goal, matched_skill_count, alignment_score, and confidence."
    )
    user_prompt = (
        f"Career goal: {career_goal}\n"
        f"Target skills: {', '.join(target_skills) if target_skills else 'None'}\n"
        f"Current skills: {', '.join(current_skills) if current_skills else 'None'}\n"
        f"Hybrid alignment score so far: {alignment_score:.2f}\n"
        f"Score breakdown: {score_details}\n"
        f"Course alignment: {course_alignment}\n\n"
        "Summarize how the recommended courses support the career goal and assess the fit."
    )
    matched_count = sum(len(item["matched_career_skills"]) for item in course_alignment)
    skill_text = ", ".join(target_skills[:5])
    payload = qwen_generate_structured(
        system_prompt,
        user_prompt,
        max_new_tokens=160,
        fallback_payload={
            "summary": (
                f"For '{career_goal}', the path focuses on {skill_text}. "
                f"The top recommendations show {matched_count} direct course-to-career skill matches."
            ),
            "career_goal": career_goal,
            "matched_skill_count": matched_count,
            "alignment_score": alignment_score,
            "confidence": alignment_score,
            "score_breakdown": score_details,
        },
    )
    payload.setdefault("alignment_score", alignment_score)
    payload.setdefault("score", payload["alignment_score"])
    payload.setdefault("confidence", payload["alignment_score"])
    logger.info(
        "recommendations.career_alignment.summary_complete total_ms=%.1f matched_skills=%s",
        (perf_counter() - summary_started_at) * 1000.0,
        matched_count,
    )
    return json.dumps(payload, ensure_ascii=False)


def calculate_alignment_score(
    target_skills: list[str],
    course_alignment: list[dict],
    current_skills: list[str] | None = None,
) -> dict[str, float | str]:
    if not target_skills:
        return {
            "base_score": 0.0,
            "llm_score": 0.0,
            "llm_adjustment": 0.0,
            "confidence": 0.0,
            "final_score": 0.0,
            "rationale": "No target skills were available.",
        }

    target_skill_set = {skill.casefold() for skill in target_skills if skill}
    if not target_skill_set:
        return {
            "base_score": 0.0,
            "llm_score": 0.0,
            "llm_adjustment": 0.0,
            "confidence": 0.0,
            "final_score": 0.0,
            "rationale": "No target skills were available.",
        }

    current_skill_set = {skill.casefold() for skill in (current_skills or []) if skill}
    student_overlap = len(target_skill_set & current_skill_set) / len(target_skill_set) if current_skill_set else 0.0

    matched_skills: set[str] = set()
    for item in course_alignment:
        for skill in item.get("matched_career_skills", []):
            if skill:
                matched_skills.add(skill.casefold())

    course_overlap = len(matched_skills) / len(target_skill_set) if course_alignment else 0.0
    base_score = min(1.0, (student_overlap * 0.6) + (course_overlap * 0.4))

    system_prompt = (
        "You are scoring career fit for a recommendation system. Return JSON with final_score, "
        "adjustment, confidence, and rationale. final_score must be between 0 and 1. "
        "Use the provided base score as your anchor and keep the adjustment small."
    )
    user_prompt = (
        f"Target skills: {', '.join(target_skills)}\n"
        f"Current skills: {', '.join(current_skills or []) if current_skills else 'None'}\n"
        f"Course alignment: {course_alignment}\n"
        f"Deterministic base score: {base_score:.2f}\n\n"
        "Return a small, bounded refinement for career fit."
    )
    payload = qwen_generate_structured(
        system_prompt,
        user_prompt,
        max_new_tokens=120,
        fallback_payload={
            "final_score": round(base_score, 2),
            "adjustment": 0.0,
            "confidence": round(base_score, 2),
            "rationale": "Fallback to deterministic career-fit score.",
        },
    )

    llm_score = coerce_float(payload.get("final_score"), base_score)
    adjustment = coerce_float(payload.get("adjustment"), 0.0)
    confidence = coerce_float(payload.get("confidence"), base_score)
    rationale = str(payload.get("rationale", "Fallback to deterministic career-fit score."))

    blended_score = (base_score * 0.7) + (llm_score * 0.3)
    blended_score += adjustment * 0.15
    if confidence < 0.35:
        blended_score = (base_score * 0.85) + (blended_score * 0.15)

    final_score = round(max(0.0, min(1.0, blended_score)), 2)
    return {
        "base_score": round(base_score, 2),
        "llm_score": round(llm_score, 2),
        "llm_adjustment": round(adjustment, 2),
        "confidence": round(confidence, 2),
        "final_score": final_score,
        "rationale": rationale,
    }


def coerce_float(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
