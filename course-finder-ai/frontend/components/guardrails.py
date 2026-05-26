"""Guardrail and explainability display components."""

from __future__ import annotations

import streamlit as st


def render_guardrails(report: dict | None) -> None:
    st.subheader("Guardrails and Explainability")
    if not report:
        st.info("No guardrail report returned yet.")
        return

    if report.get("passed"):
        st.success(report.get("summary", "Guardrails passed."))
    else:
        st.error(report.get("summary", "Guardrails detected blocking issues."))

    issues = report.get("issues", [])
    if issues:
        with st.expander("Validation details", expanded=True):
            for issue in issues:
                severity = issue.get("severity", "info").upper()
                st.write(f"**{severity} - {issue.get('check_name')}**: {issue.get('message')}")
