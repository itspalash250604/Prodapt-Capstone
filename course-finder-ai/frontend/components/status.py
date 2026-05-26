"""Status and styling components."""

from __future__ import annotations

import streamlit as st


def apply_page_style() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.6rem;
            padding-bottom: 3rem;
            max-width: 1180px;
        }
        div[data-testid="stMetric"] {
            background: #f8fafc;
            border: 1px solid #e5e7eb;
            padding: 0.75rem 0.9rem;
            border-radius: 8px;
        }
        .course-badge {
            display: inline-block;
            padding: 0.18rem 0.48rem;
            border-radius: 999px;
            border: 1px solid #d1d5db;
            background: #f9fafb;
            font-size: 0.78rem;
            margin: 0.12rem 0.18rem 0.12rem 0;
        }
        .muted {
            color: #64748b;
            font-size: 0.9rem;
        }
        .stage-card {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 0.9rem;
            background: #ffffff;
            height: 100%;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.title("Intelligent University Course Finder")
    st.caption("AI-powered course discovery with retrieval, reranking, skill gaps, learning paths, and guardrails.")


def render_api_status(is_ok: bool, message: str) -> None:
    if is_ok:
        st.sidebar.success(message)
    else:
        st.sidebar.error(message)
