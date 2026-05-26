"""Course Retrieval Agent."""

from __future__ import annotations

import json
import logging
from time import perf_counter

from app.agents.state import RecommendationState
from app.llm.service import qwen_generate_structured
from app.retrieval.reranker import CrossEncoderCourseReranker
from app.retrieval.semantic import SemanticCourseRetriever


logger = logging.getLogger(__name__)


def _rewrite_query(query: str, career_goal: str | None, current_skills: list[str]) -> str:
    system_prompt = (
        "You rewrite course search queries for a recommendation engine. "
        "Return JSON with a rewritten_query string and a short intent_summary string."
    )
    user_prompt = (
        "Original query:\n"
        f"{query}\n\n"
        f"Career goal: {career_goal or ''}\n"
        f"Current skills: {', '.join(current_skills) if current_skills else 'None'}\n\n"
        "Rewrite the query to maximize semantic course retrieval and include concise intent keywords."
    )
    payload = qwen_generate_structured(
        system_prompt,
        user_prompt,
        max_new_tokens=96,
        fallback_payload={"rewritten_query": query, "intent_summary": query},
    )
    rewritten = str(payload.get("rewritten_query", "")).strip()
    return rewritten or query


def course_retrieval_agent(state: RecommendationState) -> RecommendationState:
    """Retrieve and optionally rerank courses for the user's goal."""
    started_at = perf_counter()
    student_profile = state.get("student_profile")
    current_skills = list(getattr(student_profile, "current_skills", []) or [])
    query = _rewrite_query(state["query"], state.get("career_goal"), current_skills)
    candidate_k = state.get("candidate_k", 20)
    top_k = state.get("top_k", 8)
    use_reranker = state.get("use_reranker", True)

    retriever = SemanticCourseRetriever()
    search_started_at = perf_counter()
    candidates = retriever.search(query, top_k=candidate_k)
    search_elapsed = perf_counter() - search_started_at

    if use_reranker:
        rerank_started_at = perf_counter()
        reranker = CrossEncoderCourseReranker()
        candidates = reranker.rerank(query, candidates, top_k=top_k)
        rerank_elapsed = perf_counter() - rerank_started_at
    else:
        rerank_elapsed = 0.0
        candidates = candidates[:top_k]

    logger.info(
        "recommendations.course_retrieval.complete total_ms=%.1f search_ms=%.1f rerank_ms=%.1f candidates=%s returned=%s",
        (perf_counter() - started_at) * 1000.0,
        search_elapsed * 1000.0,
        rerank_elapsed * 1000.0,
        candidate_k,
        len(candidates),
    )

    return {
        **state,
        "retrieved_courses": candidates,
    }
