"""Career alignment display components."""

from __future__ import annotations

import streamlit as st


def render_career_alignment(alignment: dict | None) -> None:
    st.subheader("Career Alignment")
    if not alignment:
        st.info("No career alignment returned yet.")
        return

    st.write(alignment.get("summary", ""))
    skills = alignment.get("matched_skill_clusters", [])
    if skills:
        st.markdown("**Career skill clusters**")
        st.markdown(" ".join(f"<span class='course-badge'>{skill}</span>" for skill in skills), unsafe_allow_html=True)

    with st.expander("Course-to-career evidence"):
        for item in alignment.get("course_alignment", []):
            matched = ", ".join(item.get("matched_career_skills", [])) or "No direct cluster match"
            st.write(f"**{item.get('title')}**: {matched}")
