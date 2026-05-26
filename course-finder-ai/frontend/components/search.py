"""Search input component."""

from __future__ import annotations

import streamlit as st


EXAMPLE_QUERIES = [
    "machine learning engineer",
    "cybersecurity analyst",
    "beginner Python for data analysis",
    "cloud engineer with DevOps skills",
]


def render_search_form() -> tuple[bool, dict]:
    with st.form("course_search_form"):
        query = st.text_area(
            "Learning goal",
            value=st.session_state.get("last_query", ""),
            placeholder="Example: I want to become a machine learning engineer",
            height=90,
        )
        current_skills = st.text_input(
            "Current skills",
            value=st.session_state.get("last_skills", ""),
            placeholder="Python, SQL, Data Analysis",
        )
        career_goal = st.text_input(
            "Career goal",
            value=st.session_state.get("last_career_goal", ""),
            placeholder="Machine Learning Engineer",
        )

        example_cols = st.columns(len(EXAMPLE_QUERIES))
        for col, example in zip(example_cols, EXAMPLE_QUERIES):
            col.caption(example)

        submitted = st.form_submit_button("Find Courses", type="primary", use_container_width=True)

    return submitted, {
        "query": query.strip(),
        "current_skills": [skill.strip() for skill in current_skills.split(",") if skill.strip()],
        "current_skills_raw": current_skills,
        "career_goal": career_goal.strip(),
    }
