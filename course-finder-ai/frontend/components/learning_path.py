"""Learning path visualization components."""

from __future__ import annotations

import streamlit as st


def render_learning_path(path: dict | None) -> None:
    st.subheader("Learning Path")
    if not path:
        st.info("No learning path returned yet.")
        return

    st.caption(path.get("readiness_summary", ""))
    stages = path.get("stages", [])
    if not stages:
        st.info("No path stages available.")
        return

    columns = st.columns(min(len(stages), 4))
    for column, stage in zip(columns, stages):
        with column:
            st.markdown(
                f"""
                <div class="stage-card">
                  <strong>Stage {stage.get('stage_number')}: {stage.get('title')}</strong>
                  <p class="muted">{stage.get('purpose')}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            for course in stage.get("courses", []):
                missing_skill = course.get("missing_skill")
                suffix = f" fills {missing_skill}" if missing_skill else ""
                st.write(f"- {course.get('title')} [{course.get('difficulty')}]{suffix}")

    st.caption(path.get("note", ""))
