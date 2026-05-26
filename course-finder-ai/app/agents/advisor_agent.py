"""Learning Advisor Agent."""

from __future__ import annotations

import json
import logging
from time import perf_counter

from app.agents.state import RecommendationState
from app.llm.service import qwen_generate_structured, qwen_generate_text


logger = logging.getLogger(__name__)


def learning_advisor_agent(state: RecommendationState) -> RecommendationState:
    """Create the final student-facing recommendation summary."""
    started_at = perf_counter()
    final_response = build_final_response(state)
    logger.info(
        "recommendations.advisor.complete total_ms=%.1f",
        (perf_counter() - started_at) * 1000.0,
    )
    return {
        **state,
        "final_response": final_response,
    }


def build_final_response(state: RecommendationState) -> str:
    # Build deterministic payload to use as a fallback and for inspection
    started_at = perf_counter()
    payload = build_final_payload(state)

    system_prompt = (
        "You are the final recommendation narrator for a course discovery system. "
        "Produce two human-readable text summaries for the user: first a structured paragraph that explains the recommendations and why they fit the learner, "
        "and second a condensed one-sentence summary. Return only plain text with the following markers:\n"
        "---STRUCTURED_PARAGRAPH---\n<structured paragraph>\n---CONDENSED---\n<one-line condensed summary>\n"
        "Be concise and avoid inventing factual course metadata not present in the provided input."
    )

    user_prompt = (
        f"Query: {state['query']}\n\n"
        f"Top courses: {serialize_courses(state.get('retrieved_courses', []))}\n\n"
        f"Skill gaps: {serialize_skill_gaps(state.get('skill_gap_results', []))}\n\n"
        f"Learning path: {serialize_learning_path(state.get('learning_path'))}\n\n"
        f"Career alignment: {serialize_career_alignment(state.get('career_alignment'))}\n\n"
        f"Guardrails: {serialize_guardrails(state.get('guardrail_report'))}\n\n"
        "Return only the two text sections with the markers specified."
    )

    # Ask the LLM for textual summaries (not JSON). Fall back to deterministic text.
    try:
        llm_text = qwen_generate_text(system_prompt, user_prompt, max_new_tokens=512, temperature=0.0)
    except Exception:
        llm_text = ""

    result: str
    if not llm_text:
        # deterministic fallback: build textual structured paragraph and condensed summary
        result = build_textual_fallback(payload)
    elif "---STRUCTURED_PARAGRAPH---" in llm_text and "---CONDENSED---" in llm_text:
        result = llm_text.strip()
    else:
        # If LLM returned plain text without markers, wrap it into structured+condensed form
        structured = llm_text.strip()
        condensed = (
            structured.split(". ")[0][:200] + "..." if structured else "Summary not available"
        )
        result = f"---STRUCTURED_PARAGRAPH---\n{structured}\n---CONDENSED---\n{condensed}"

    logger.info(
        "recommendations.advisor.render_complete total_ms=%.1f llm_used=%s",
        (perf_counter() - started_at) * 1000.0,
        bool(llm_text),
    )
    return result


def build_fallback_response(state: RecommendationState) -> str:
    return build_textual_fallback(build_final_payload(state))


def build_textual_fallback(payload: dict[str, object]) -> str:
    """Create a deterministic structured paragraph and condensed summary from payload."""
    query = payload.get("query", "")
    recs = payload.get("recommendations", [])
    rec_lines = []
    for r in recs[:5]:
        title = r.get("title") or r.get("course_id")
        org = r.get("organization")
        score = r.get("score")
        rec_lines.append(f"{title} ({org}) — match {score:.0%}")

    structured = (
        f"Recommendations for '{query}': The top matches are {', '.join(rec_lines)}. "
        "These recommendations are based on retrieval and reranking scores, inferred prerequisites, and your provided profile."
    )
    condensed = (
        f"Top picks: {', '.join([r.get('title') for r in recs[:3]])}."
    )
    return f"---STRUCTURED_PARAGRAPH---\n{structured}\n---CONDENSED---\n{condensed}"


def build_final_payload(state: RecommendationState) -> dict[str, object]:
    courses = state.get("retrieved_courses", [])
    skill_gaps = state.get("skill_gap_results", [])
    learning_path = state.get("learning_path")
    career_alignment = state.get("career_alignment")
    guardrail_report = state.get("guardrail_report")

    recommendations = []
    for index, course in enumerate(courses[:5], start=1):
        metadata = course.metadata or {}
        # Build a minimal recommendation record and enrich with LLM-generated rationale/description
        base_rec = {
            "rank": index,
            "course_id": course.course_id,
            "title": course.title,
            "organization": course.organization,
            "difficulty": metadata.get("difficulty", ""),
            "course_type": metadata.get("course_type", ""),
            "score": course.score,
        }

        enrichment = generate_course_enrichment(course, state)
        base_rec.update(
            {
                "description": enrichment.get("description"),
                "rationale": enrichment.get("rationale"),
                "time_to_complete": enrichment.get("time_to_complete"),
                "match_percentage": enrichment.get("match_percentage") if enrichment.get("match_percentage") is not None else float(course.score),
            }
        )

        recommendations.append(base_rec)

    readiness = []
    for gap in skill_gaps[:5]:
        readiness.append(
            {
                "course_id": gap.course_id,
                "course_title": gap.course_title,
                "readiness_label": gap.readiness_label,
                "readiness_score": gap.readiness_score,
                "missing_skills": gap.missing_skills[:5],
                "note": gap.note,
            }
        )

    path_payload = None
    if learning_path:
        path_payload = {
            "goal": learning_path.goal,
            "readiness_summary": learning_path.readiness_summary,
            "note": learning_path.note,
            "total_courses": learning_path.total_courses,
            "stages": [
                {
                    "stage_number": stage.stage_number,
                    "title": stage.title,
                    "purpose": stage.purpose,
                    "courses": [
                        {
                            "course_id": course.course_id,
                            "title": course.title,
                            "organization": course.organization,
                            "difficulty": course.difficulty,
                            "course_type": course.course_type,
                            "missing_skill": course.missing_skill,
                            "reason": course.reason,
                        }
                        for course in stage.courses
                    ],
                }
                for stage in learning_path.stages
            ],
        }

    guardrails_payload = None
    if guardrail_report:
        guardrails_payload = {
            "passed": guardrail_report.passed,
            "summary": guardrail_report.summary,
            "issues": [
                {
                    "check_name": issue.check_name,
                    "severity": issue.severity,
                    "message": issue.message,
                    "course_id": issue.course_id,
                    "stage_number": issue.stage_number,
                }
                for issue in guardrail_report.issues
            ],
        }

    return {
        "query": state["query"],
        "recommendations": recommendations,
        "readiness": readiness,
        "learning_path": path_payload,
        "career_alignment": career_alignment,
        "guardrails": guardrails_payload,
        "note": (
            "Recommendations are grounded in the course dataset, inferred prerequisites, "
            "and retrieval/reranking scores. Inferred prerequisites are guidance, not official requirements."
        ),
    }


def serialize_courses(courses: list[object]) -> str:
    lines = []
    for course in courses[:5]:
        metadata = getattr(course, "metadata", {}) or {}
        lines.append(
            f"{getattr(course, 'title', '')} ({getattr(course, 'organization', '')}) "
            f"[{metadata.get('difficulty', '')}, {metadata.get('course_type', '')}] score={getattr(course, 'score', 0.0):.4f}"
        )
    return "\n".join(lines) or "None"


def serialize_skill_gaps(skill_gaps: list[object]) -> str:
    lines = []
    for gap in skill_gaps[:5]:
        lines.append(
            f"{getattr(gap, 'course_title', '')}: readiness={getattr(gap, 'readiness_score', 0.0):.0%}, "
            f"missing={', '.join(getattr(gap, 'missing_skills', [])[:5]) or 'None'}"
        )
    return "\n".join(lines) or "None"


def serialize_learning_path(learning_path: object | None) -> str:
    if learning_path is None:
        return "None"
    lines = [f"Goal: {getattr(learning_path, 'goal', '')}"]
    lines.append(f"Readiness summary: {getattr(learning_path, 'readiness_summary', '')}")
    for stage in getattr(learning_path, 'stages', []):
        lines.append(f"Stage {getattr(stage, 'stage_number', '?')}: {getattr(stage, 'title', '')}")
        for course in getattr(stage, 'courses', []):
            lines.append(f"- {getattr(course, 'title', '')} ({getattr(course, 'organization', '')})")
    lines.append(f"Note: {getattr(learning_path, 'note', '')}")
    return "\n".join(lines)


def serialize_career_alignment(career_alignment: object | None) -> str:
    if not career_alignment:
        return "None"
    return str(career_alignment)


def serialize_guardrails(guardrail_report: object | None) -> str:
    if not guardrail_report:
        return "None"
    issues = getattr(guardrail_report, 'issues', [])
    lines = [f"passed={getattr(guardrail_report, 'passed', False)}", f"summary={getattr(guardrail_report, 'summary', '')}"]
    for issue in issues[:5]:
        lines.append(
            f"- {getattr(issue, 'severity', '')} [{getattr(issue, 'check_name', '')}] {getattr(issue, 'message', '')}"
        )
    return "\n".join(lines)


def generate_course_enrichment(course: object, state: RecommendationState) -> dict[str, object]:
    """Generate a short description, rationale, time estimate and match pct for a course.

    This uses the Qwen structured generator but falls back to deterministic fields
    extracted from the course metadata/document when the model is unavailable.
    """
    started_at = perf_counter()
    metadata = getattr(course, "metadata", {}) or {}
    # conservative fallbacks
    fallback = {
        "description": metadata.get("description") or (getattr(course, "document", "")[:300] or None),
        "rationale": None,
        "time_to_complete": metadata.get("duration") or metadata.get("time_to_complete") or metadata.get("hours") or None,
        "match_percentage": float(getattr(course, "score", 0.0)),
    }

    system_prompt = (
        "You are a concise assistant that summarizes a course and explains why it fits a learner. "
        "Return a JSON object with keys: description, rationale, time_to_complete, match_percentage. "
        "Be conservative: do not invent factual course details not present in the provided metadata or document. "
    )

    user_prompt = (
        f"Course title: {getattr(course, 'title', '')}\n"
        f"Organization: {getattr(course, 'organization', '')}\n"
        f"Metadata: {json.dumps(metadata)}\n"
        f"Document snippet: {getattr(course, 'document', '')[:800]}\n\n"
        f"Student query: {state.get('query')}\n"
        f"Student current skills: {', '.join(state.get('current_skills', []) or [])}\n"
        f"Student career goal: {state.get('career_goal') or ''}\n\n"
        "Return only valid JSON. For match_percentage return a number between 0.0 and 1.0."
    )

    try:
        payload = qwen_generate_structured(system_prompt, user_prompt, max_new_tokens=200, fallback_payload=fallback)
    except Exception:
        payload = fallback

    # Ensure numeric match_percentage
    try:
        if payload.get("match_percentage") is None:
            payload["match_percentage"] = float(getattr(course, "score", 0.0))
        else:
            payload["match_percentage"] = float(payload.get("match_percentage"))
    except Exception:
        payload["match_percentage"] = float(getattr(course, "score", 0.0))

    # Attach preparatory resources inferred from the structured skill-gap results.
    try:
        payload["preparatory_resources"] = recommend_prep_resources_for_course(course, state)
    except Exception:
        payload["preparatory_resources"] = []

    logger.info(
        "recommendations.course_enrichment.complete total_ms=%.1f course_id=%s",
        (perf_counter() - started_at) * 1000.0,
        getattr(course, "course_id", None),
    )

    return payload


def recommend_prep_resources_for_course(course: object, state: RecommendationState) -> list[dict[str, object]]:
    """Return preparatory resources for a course using structured skill-gap data.

    Preference order:
    1. Use `skill_gap_results` for the matching course id.
    2. Fall back to quality-issue text parsing if needed.
    3. Use a small static resource map when the analyzer has no built-in course suggestions.
    """
    # Simple static mapping from skill keywords to a small set of curated resources.
    RESOURCE_MAP: dict[str, list[dict[str, str]]] = {
        "Linear Algebra": [
            {"title": "Khan Academy: Linear Algebra", "url": "https://www.khanacademy.org/math/linear-algebra", "source": "Khan Academy", "estimated_time": "6-20 hours"},
            {"title": "MIT OCW 18.06 (Gilbert Strang)", "url": "https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/", "source": "MIT OCW", "estimated_time": "4-8 weeks"},
        ],
        "Databases": [
            {"title": "SQLBolt Interactive SQL Lessons", "url": "https://sqlbolt.com/", "source": "SQLBolt", "estimated_time": "2-6 hours"},
            {"title": "Intro to Databases (Stanford/Coursera)", "url": "https://www.coursera.org/learn/databases", "source": "Coursera", "estimated_time": "2-4 weeks"},
        ],
        "Spreadsheet Software": [
            {"title": "Google Sheets Essential Training", "url": "https://www.linkedin.com/learning/google-sheets-essential-training-2019", "source": "LinkedIn Learning", "estimated_time": "2-6 hours"},
        ],
        "Cloud Computing": [
            {"title": "Intro to Cloud Computing (Coursera)", "url": "https://www.coursera.org/learn/cloud-computing", "source": "Coursera", "estimated_time": "3-10 hours"},
        ],
        "Operating Systems": [
            {"title": "Operating Systems: Three Easy Pieces", "url": "http://pages.cs.wisc.edu/~remzi/OSTEP/", "source": "OSTEP", "estimated_time": "1-4 weeks"},
        ],
        "Computer Networking": [
            {"title": "Computer Networking: Principles, Protocols and Practice", "url": "https://inl.info.ucl.ac.be/teaching/Networking/book/", "source": "Open Book", "estimated_time": "1-4 weeks"},
        ],
    }

    course_id = getattr(course, "course_id", None)
    missing_skills: list[str] = []
    resources_by_skill: dict[str, list[dict[str, object]]] = {}

    for gap in state.get("skill_gap_results", []) or []:
        gap_course_id = getattr(gap, "course_id", None)
        if gap_course_id != course_id:
            continue

        missing_skills.extend(getattr(gap, "missing_skills", []) or [])
        for foundational in getattr(gap, "foundational_courses", []) or []:
            skill = getattr(foundational, "missing_skill", None)
            if not skill:
                continue
            resources_by_skill.setdefault(skill, []).append(
                {
                    "title": getattr(foundational, "title", skill),
                    "url": f"https://www.google.com/search?q={getattr(foundational, 'title', skill).replace(' ', '+')}",
                    "source": getattr(foundational, "organization", "Recommended course"),
                    "estimated_time": "Varies",
                    "reason": getattr(foundational, "reason", None),
                }
            )

    if not missing_skills:
        for issue in state.get("quality_issues", []) or []:
            try:
                check_name = getattr(issue, "check_name", None) or issue.get("check_name") if isinstance(issue, dict) else None
                issue_course_id = getattr(issue, "course_id", None) or issue.get("course_id") if isinstance(issue, dict) else None
                message = getattr(issue, "message", None) or issue.get("message") if isinstance(issue, dict) else str(issue)
            except Exception:
                continue

            if check_name != "prerequisite_validation" or issue_course_id != course_id:
                continue

            parts = None
            if ":" in message:
                parts = message.split(":", 1)[1]
            elif "gaps" in message.lower():
                parts = message

            if parts:
                for s in parts.split(","):
                    skill = s.strip().strip(".")
                    if skill:
                        missing_skills.append(skill)

    # Deduplicate while preserving order.
    missing_skills = list(dict.fromkeys(missing_skills))

    preparatory: list[dict[str, object]] = []
    for skill in missing_skills:
        if skill in resources_by_skill:
            preparatory.append({"skill": skill, "resources": resources_by_skill[skill]})
            continue

        resources = RESOURCE_MAP.get(skill)
        if resources:
            preparatory.append({"skill": skill, "resources": resources})
        else:
            # generic fallback suggestion
            preparatory.append({"skill": skill, "resources": [{"title": f"Intro to {skill}", "url": "https://www.google.com/search?q=intro+%s" % skill.replace(' ', '+'), "source": "Web", "estimated_time": "2-10 hours"}]})

    return preparatory
