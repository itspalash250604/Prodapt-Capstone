"""LangGraph workflow builder for the recommendation system."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.advisor_agent import learning_advisor_agent
from app.agents.career_alignment_agent import career_alignment_agent
from app.agents.course_retrieval_agent import course_retrieval_agent
from app.agents.guardrails_agent import guardrails_agent
from app.agents.learning_path_agent import learning_path_planning_agent
from app.agents.skill_gap_agent import skill_gap_analysis_agent
from app.agents.state import RecommendationState


def build_recommendation_graph():
    """Build and compile the linear multi-agent recommendation graph."""
    graph = StateGraph(RecommendationState)

    graph.add_node("course_retrieval_agent", course_retrieval_agent)
    graph.add_node("skill_gap_analysis_agent", skill_gap_analysis_agent)
    graph.add_node("learning_path_planning_agent", learning_path_planning_agent)
    graph.add_node("career_alignment_agent", career_alignment_agent)
    graph.add_node("guardrails_agent", guardrails_agent)
    graph.add_node("learning_advisor_agent", learning_advisor_agent)

    graph.add_edge(START, "course_retrieval_agent")
    graph.add_edge("course_retrieval_agent", "skill_gap_analysis_agent")
    graph.add_edge("skill_gap_analysis_agent", "learning_path_planning_agent")
    graph.add_edge("learning_path_planning_agent", "career_alignment_agent")
    graph.add_edge("career_alignment_agent", "guardrails_agent")
    graph.add_edge("guardrails_agent", "learning_advisor_agent")
    graph.add_edge("learning_advisor_agent", END)

    return graph.compile()
