"""Sidebar filters and settings."""

from __future__ import annotations

import streamlit as st

from frontend.config import COURSE_TYPE_OPTIONS, DIFFICULTY_OPTIONS


def render_sidebar_filters() -> dict:
    st.sidebar.header("Filters")
    difficulty = st.sidebar.selectbox("Difficulty", DIFFICULTY_OPTIONS)
    min_rating = st.sidebar.slider("Minimum rating", 0.0, 5.0, 0.0, 0.1)
    organization = st.sidebar.text_input("Provider contains", placeholder="Google, IBM, Stanford")
    course_type = st.sidebar.selectbox("Course type", COURSE_TYPE_OPTIONS)
    duration = st.sidebar.text_input("Duration contains", placeholder="1 - 3 Months")

    st.sidebar.header("Recommendation Settings")
    candidate_k = st.sidebar.slider("Candidate pool", 5, 50, 12, 1)
    top_k = st.sidebar.slider("Top recommendations", 3, 20, 6, 1)
    max_path_courses = st.sidebar.slider("Max path courses", 3, 12, 6, 1)
    use_reranker = st.sidebar.toggle("Use BGE reranker", value=False)

    return {
        "difficulty": difficulty,
        "min_rating": min_rating,
        "organization": organization.strip(),
        "course_type": course_type,
        "duration": duration.strip(),
        "candidate_k": candidate_k,
        "top_k": min(top_k, candidate_k),
        "max_path_courses": max_path_courses,
        "use_reranker": use_reranker,
    }


def filter_courses(courses: list[dict], filters: dict) -> list[dict]:
    filtered = []
    for course in courses:
        metadata = course.get("metadata", {})
        if filters["difficulty"] != "Any" and metadata.get("difficulty") != filters["difficulty"]:
            continue
        if filters["course_type"] != "Any" and metadata.get("course_type") != filters["course_type"]:
            continue
        if filters["organization"] and filters["organization"].casefold() not in course.get("organization", "").casefold():
            continue
        if filters["duration"] and filters["duration"].casefold() not in str(metadata.get("duration", "")).casefold():
            continue
        rating = metadata.get("rating")
        if rating not in ("", None) and float(rating) < filters["min_rating"]:
            continue
        filtered.append(course)
    return filtered
