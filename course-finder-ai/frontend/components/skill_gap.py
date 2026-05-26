"""Skill gap display components."""

from __future__ import annotations

import streamlit as st

from frontend.utils.formatting import as_percent, compact_list


def render_skill_gaps(skill_gaps: list[dict]) -> None:
    st.subheader("Skill Gap Analysis")
    if not skill_gaps:
        st.info("No skill gap analysis returned yet.")
        return

    selected = skill_gaps[0]
    col_a, col_b = st.columns([1, 2])
    col_a.metric("Readiness", as_percent(selected.get("readiness_score")))
    col_b.write(f"**Top course:** {selected.get('course_title', 'N/A')}")
    col_b.write(f"**Readiness label:** {selected.get('readiness_label', 'N/A')}")

    tab_required, tab_missing, tab_foundations = st.tabs(["Preparation Skills", "Missing Skills", "Foundations"])
    with tab_required:
        st.write(compact_list(selected.get("inferred_prerequisites", [])))
    with tab_missing:
        missing = selected.get("missing_skills", [])
        if missing:
            for skill in missing:
                st.warning(skill)
        else:
            st.success("No major missing skills detected for the top course.")
    with tab_foundations:
        foundations = selected.get("foundational_courses", [])
        if foundations:
            for item in foundations:
                st.write(f"**{item.get('missing_skill')}** -> {item.get('title')} ({item.get('organization')})")
        else:
            st.write("No foundational course suggestions needed.")
