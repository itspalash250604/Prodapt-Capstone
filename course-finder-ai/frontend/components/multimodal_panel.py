"""Future multimodal input placeholders."""

from __future__ import annotations

import streamlit as st


def render_multimodal_panel() -> None:
    st.sidebar.header("Future Multimodal Inputs")
    st.sidebar.file_uploader("PDF profile or syllabus", type=["pdf"], disabled=True)
    st.sidebar.file_uploader("Course screenshot", type=["png", "jpg", "jpeg"], disabled=True)
    st.sidebar.button("Voice input coming soon", disabled=True, use_container_width=True)
    st.sidebar.caption("These controls are placeholders for future PDF, image, and voice extraction endpoints.")
