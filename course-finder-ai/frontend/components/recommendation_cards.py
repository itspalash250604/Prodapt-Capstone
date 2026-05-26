"""Recommendation card components."""

from __future__ import annotations

import streamlit as st

from frontend.utils.formatting import format_rating, format_score, split_skills


def render_recommendations(courses: list[dict]) -> None:
    st.subheader("Recommended Courses")
    if not courses:
        st.info("No courses match the current filters. Try loosening the sidebar filters.")
        return

    for index, course in enumerate(courses, start=1):
        metadata = course.get("metadata", {})
        title = course.get("title", "Untitled course")
        provider = course.get("organization", "Unknown provider")
        difficulty = metadata.get("difficulty", "N/A")
        course_type = metadata.get("course_type", "N/A")
        duration = metadata.get("duration", "N/A")
        rating = format_rating(metadata.get("rating"))
        score = format_score(course.get("score"))
        skills = split_skills(metadata.get("skills_text"), limit=12)

        with st.expander(f"{index}. {title} - {provider}", expanded=index == 1):
            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric("Score", score)
            col_b.metric("Rating", rating)
            col_c.metric("Difficulty", difficulty)
            col_d.metric("Duration", duration)

            st.markdown(f"**Type:** {course_type}")
            if skills:
                st.markdown("**Skills covered**")
                st.markdown(" ".join(f"<span class='course-badge'>{skill}</span>" for skill in skills), unsafe_allow_html=True)

            st.markdown("**Why this course was recommended**")
            st.write(
                "This course was selected because its title, provider, difficulty, and skills are semantically aligned "
                "with your learning goal and ranked by the recommendation pipeline."
            )
