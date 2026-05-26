"""Glassmorphism Streamlit dashboard wired to the FastAPI recommendation backend."""

from __future__ import annotations

from datetime import datetime, timezone
import html
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from frontend.config import API_BASE_URL
from frontend.services.api_client import ApiClientError, check_health, get_recommendations


PAGE_TITLE = "Neural Fabric Course Command Center"
PAGE_ICON = "◼"
ACCENT_CYAN = "#00F2FE"
ACCENT_PURPLE = "#6366F1"
TEXT_PRIMARY = "#F8FAFC"
TEXT_SECONDARY = "#94A3B8"
BG_MAIN = "#080B11"
PANEL_BG = "rgba(30, 41, 59, 0.45)"

SCENARIOS = [
    ("Machine Learning Engineer", ["Python", "Data Analysis"], "machine learning engineer"),
    ("Cybersecurity Analyst", ["Networking", "Linux"], "cybersecurity analyst"),
    ("Cloud Architect", ["AWS", "Networking"], "cloud architect"),
    ("Data Engineer", ["SQL", "Python"], "data engineer"),
]


def ensure_state() -> None:
    defaults = {
        "query": SCENARIOS[0][0],
        "skills_raw": ", ".join(SCENARIOS[0][1]),
        "career_goal": SCENARIOS[0][2],
        "candidate_k": 20,
        "top_k": 8,
        "max_path_courses": 6,
        "use_reranker": True,
        "last_response": None,
        "last_error": "",
        "last_refresh": datetime.now(timezone.utc),
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def esc(value: object) -> str:
    return html.escape(str(value))


def format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%d %b %Y • %H:%M UTC")


def inject_styles() -> None:
    st.markdown(
        f"""
        <style>
        :root {{
            --bg-main: {BG_MAIN};
            --panel-bg: {PANEL_BG};
            --text-primary: {TEXT_PRIMARY};
            --text-secondary: {TEXT_SECONDARY};
            --accent-cyan: {ACCENT_CYAN};
            --accent-purple: {ACCENT_PURPLE};
            --glass-border: rgba(255, 255, 255, 0.08);
            --glass-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
            --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        html, body, [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] > .main {{
            background:
                radial-gradient(circle at 15% 20%, rgba(0, 242, 254, 0.14), transparent 26%),
                radial-gradient(circle at 85% 12%, rgba(99, 102, 241, 0.18), transparent 28%),
                radial-gradient(circle at 50% 88%, rgba(0, 242, 254, 0.08), transparent 24%),
                linear-gradient(180deg, #05070c 0%, #080b11 48%, #0b0f19 100%);
            color: var(--text-primary);
        }}

        [data-testid="stAppViewContainer"]::before {{
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            background-image:
                linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
            background-size: 42px 42px;
            mask-image: linear-gradient(180deg, rgba(0,0,0,0.55), rgba(0,0,0,0.1));
        }}

        header, footer {{ visibility: hidden; }}

        .block-container {{
            padding-top: 1rem;
            padding-bottom: 1.5rem;
            max-width: 1600px;
        }}

        [data-testid="stSidebar"] {{
            background: rgba(7, 10, 18, 0.86);
            border-right: 1px solid rgba(255, 255, 255, 0.06);
        }}

        .glass-panel {{
            background: var(--panel-bg);
            backdrop-filter: blur(12px) saturate(180%);
            border: 1px solid var(--glass-border);
            box-shadow: var(--glass-shadow);
            border-radius: 24px;
            padding: 1.15rem 1.2rem;
        }}

        .hero {{
            position: relative;
            overflow: hidden;
            border-radius: 28px;
            padding: 1.45rem 1.5rem;
            background:
                linear-gradient(135deg, rgba(30, 41, 59, 0.60), rgba(15, 23, 42, 0.35)),
                radial-gradient(circle at top right, rgba(99, 102, 241, 0.22), transparent 34%),
                radial-gradient(circle at bottom left, rgba(0, 242, 254, 0.17), transparent 28%);
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 18px 45px rgba(0, 0, 0, 0.42);
        }}

        .hero-grid {{
            display: grid;
            grid-template-columns: 1.35fr 0.95fr;
            gap: 1rem;
            align-items: center;
        }}

        .eyebrow {{
            letter-spacing: 0.18em;
            text-transform: uppercase;
            font-size: 0.72rem;
            color: rgba(148, 163, 184, 0.95);
            margin-bottom: 0.35rem;
        }}

        .title {{
            font-size: clamp(2rem, 4.8vw, 3.6rem);
            line-height: 0.98;
            font-weight: 800;
            color: var(--text-primary);
            margin: 0;
            text-shadow: 0 0 24px rgba(0, 242, 254, 0.18);
        }}

        .subtitle {{
            color: var(--text-secondary);
            margin-top: 0.6rem;
            font-size: 0.98rem;
            max-width: 62rem;
        }}

        .status-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.7rem;
            justify-content: flex-end;
            align-items: center;
        }}

        .status-pill, .time-pill {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.65rem 0.9rem;
            border-radius: 999px;
            background: rgba(15, 23, 42, 0.55);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: var(--text-primary);
        }}

        .status-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #22c55e;
            box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.35);
            animation: pulse 1.6s infinite;
        }}

        @keyframes pulse {{
            0% {{ box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.40); }}
            70% {{ box-shadow: 0 0 0 16px rgba(34, 197, 94, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }}
        }}

        .section-label {{
            display: flex;
            align-items: center;
            gap: 0.65rem;
            margin: 1rem 0 0.8rem;
            color: var(--text-primary);
            text-transform: uppercase;
            letter-spacing: 0.14em;
            font-size: 0.75rem;
            font-weight: 700;
        }}

        .section-label::before {{
            content: "";
            width: 36px;
            height: 1px;
            background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple));
        }}

        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 1rem;
        }}

        .kpi-card {{
            padding: 1rem 1rem 0.9rem;
            border-radius: 22px;
            background: rgba(30, 41, 59, 0.45);
            backdrop-filter: blur(12px) saturate(180%);
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
            transition: var(--transition);
        }}

        .kpi-card:hover, .glass-panel:hover, [data-testid="stForm"]:hover {{
            border-color: rgba(0, 242, 254, 0.22);
            transform: translateY(-2px);
            box-shadow: 0 12px 38px rgba(0, 0, 0, 0.46);
        }}

        .kpi-label {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.75rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.13em;
            font-size: 0.72rem;
            font-weight: 700;
        }}

        .kpi-value {{
            margin-top: 0.55rem;
            font-size: clamp(1.45rem, 2.6vw, 2rem);
            font-weight: 800;
            color: var(--text-primary);
        }}

        .kpi-meta {{
            margin-top: 0.2rem;
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}

        .chart-title {{
            color: var(--text-primary);
            font-size: 1rem;
            font-weight: 800;
            margin-bottom: 0.35rem;
        }}

        .chart-subtitle {{
            color: var(--text-secondary);
            margin-bottom: 1rem;
            font-size: 0.9rem;
        }}

        .data-table table {{
            width: 100%;
            border-collapse: collapse;
            color: var(--text-primary);
        }}

        .data-table th, .data-table td {{
            border-bottom: 1px solid rgba(255,255,255,0.06);
            padding: 0.8rem 0.7rem;
            text-align: left;
            font-size: 0.9rem;
        }}

        .data-table th {{
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-size: 0.71rem;
        }}

        .mini-pill {{
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.38rem 0.6rem;
            border-radius: 999px;
            font-size: 0.76rem;
            background: rgba(255,255,255,0.05);
            color: var(--text-primary);
        }}

        .mini-pill.good {{ color: #8ef0c6; }}
        .mini-pill.warn {{ color: #fde68a; }}
        .mini-pill.bad {{ color: #fca5a5; }}

        .helper-text {{
            color: var(--text-secondary);
            font-size: 0.88rem;
            line-height: 1.55;
        }}

        .stButton > button {{
            width: 100%;
            border-radius: 14px;
            border: 1px solid rgba(255,255,255,0.08);
            background: linear-gradient(135deg, rgba(0, 242, 254, 0.18), rgba(99, 102, 241, 0.18));
            color: var(--text-primary);
            transition: var(--transition);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
        }}

        .stButton > button:hover {{
            transform: translateY(-1px);
            border-color: rgba(0, 242, 254, 0.35);
            background: linear-gradient(135deg, rgba(0, 242, 254, 0.28), rgba(99, 102, 241, 0.24));
        }}

        .subtle-rule {{
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.14), transparent);
            margin: 1rem 0;
        }}

        @media (max-width: 1180px) {{
            .kpi-grid, .hero-grid {{ grid-template-columns: 1fr; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def html_block(content: str) -> None:
    st.markdown(content, unsafe_allow_html=True)


def parse_skills(raw: str) -> list[str]:
    return [skill.strip() for skill in raw.split(",") if skill.strip()]


def metric_card(label: str, value: str, meta: str, tone: str = "good") -> str:
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{esc(label)}<span class="mini-pill {tone}">{esc(tone.upper())}</span></div>
        <div class="kpi-value">{esc(value)}</div>
        <div class="kpi-meta">{esc(meta)}</div>
    </div>
    """


def render_header() -> None:
    try:
        health = check_health()
        online = True
        service_label = f"{health.get('service', 'course-finder-ai')} {health.get('version', 'v1')}"
        status_text = "SYSTEM STATUS: OPERATIONAL"
    except ApiClientError as exc:
        online = False
        service_label = "backend offline"
        status_text = "SYSTEM STATUS: DEGRADED"
        st.session_state["last_error"] = str(exc)

    timestamp = format_timestamp(datetime.now(timezone.utc))
    html_block(
        f"""
        <div class="hero">
            <div class="hero-grid">
                <div>
                    <div class="eyebrow">Enterprise recommendation control plane</div>
                    <h1 class="title">{PAGE_TITLE}</h1>
                    <div class="subtitle">A glassmorphism dashboard that sends your query, skills, and career goal into the FastAPI backend, then renders live courses, skill gaps, learning path, and guardrail output.</div>
                </div>
                <div class="status-row">
                    <div class="status-pill"><span class="status-dot"></span><strong>{esc(status_text)}</strong></div>
                    <div class="time-pill">{esc(timestamp)}</div>
                    <div class="time-pill">API: {esc(API_BASE_URL)}</div>
                    <div class="time-pill">{esc(service_label)}</div>
                    <div class="time-pill">{esc('ONLINE' if online else 'OFFLINE')}</div>
                </div>
            </div>
        </div>
        """
    )


def render_controls() -> dict[str, object]:
    html_block('<div class="section-label">Control & Action Zone</div>')
    with st.form("recommendation_form"):
        html_block('<div class="glass-panel"><div class="chart-title">Mission Controls</div><div class="chart-subtitle">These inputs are posted directly to the backend recommendation endpoint.</div>')
        left, middle, right = st.columns([1.2, 1.0, 1.0])
        with left:
            query = st.text_input("Query", value=st.session_state["query"], label_visibility="collapsed")
            html_block('<div class="helper-text">Current Skills</div>')
            skills_raw = st.text_input("Skills", value=st.session_state["skills_raw"], label_visibility="collapsed")
        with middle:
            html_block('<div class="helper-text">Career Goal</div>')
            career_goal = st.text_input("Career Goal", value=st.session_state["career_goal"], label_visibility="collapsed")
            html_block('<div style="height:0.4rem"></div><div class="helper-text">Candidate / Top K</div>')
            candidate_k = st.slider("candidate_k", 1, 50, int(st.session_state["candidate_k"]), label_visibility="collapsed")
            top_k = st.slider("top_k", 1, 20, int(st.session_state["top_k"]), label_visibility="collapsed")
        with right:
            html_block('<div class="helper-text">Path & Ranker</div>')
            max_path_courses = st.slider("max_path_courses", 1, 12, int(st.session_state["max_path_courses"]), label_visibility="collapsed")
            use_reranker = st.toggle("Use reranker", value=bool(st.session_state["use_reranker"]))
            submitted = st.form_submit_button("Run Recommendation Pipeline")
            html_block('<div class="helper-text" style="margin-top:0.55rem;">The backend validates prerequisites, ranks candidates, plans the path, and returns the final advisory response.</div>')
        html_block('</div>')

    return {
        "submitted": submitted,
        "query": query,
        "skills_raw": skills_raw,
        "career_goal": career_goal,
        "candidate_k": candidate_k,
        "top_k": top_k,
        "max_path_courses": max_path_courses,
        "use_reranker": use_reranker,
    }


def render_empty_state() -> None:
    html_block(
        """
        <div class="glass-panel">
            <div class="chart-title">Awaiting a recommendation run</div>
            <div class="chart-subtitle">Submit a query to fetch live results from the backend.</div>
            <div class="kpi-grid" style="grid-template-columns: repeat(3, minmax(0, 1fr)); margin-top: 0.9rem;">
                <div class="kpi-card"><div class="kpi-label">Semantic Retrieval</div><div class="kpi-meta">Ranks courses by relevance and signal strength.</div></div>
                <div class="kpi-card"><div class="kpi-label">Skill Gap Analysis</div><div class="kpi-meta">Highlights missing preparation skills.</div></div>
                <div class="kpi-card"><div class="kpi-label">Learning Path</div><div class="kpi-meta">Builds a sequenced plan from foundations to advanced topics.</div></div>
            </div>
        </div>
        """
    )


def render_metrics(response: dict[str, object]) -> None:
    courses = response.get("courses", []) or []
    learning_path = response.get("learning_path") or {}
    guardrails = response.get("guardrails") or {}

    course_scores = [float(course.get("score", 0.0)) for course in courses if isinstance(course, dict)]
    avg_score = round(float(np.mean(course_scores)), 2) if course_scores else 0.0
    stage_count = len(learning_path.get("stages", []) or [])
    issue_count = len(guardrails.get("issues", []) or []) if isinstance(guardrails, dict) else 0

    cards = [
        ("Returned Courses", str(len(courses)), "Courses returned by the backend", "good"),
        ("Average Score", f"{avg_score:.2f}", "Mean retrieval score", "good" if avg_score >= 0.5 else "warn"),
        ("Learning Stages", str(stage_count), "Stages in the generated path", "good" if stage_count else "warn"),
        ("Guardrail Issues", str(issue_count), "Validation or prerequisite findings", "warn" if issue_count else "good"),
    ]

    html_block('<div class="section-label">Core Analytics Grid</div>')
    cols = st.columns(4)
    for col, (label, value, meta, tone) in zip(cols, cards):
        with col:
            html_block(metric_card(label, value, meta, tone))


def render_courses(response: dict[str, object]) -> None:
    courses = response.get("courses", []) or []
    html_block('<div class="section-label">Retrieved Courses</div>')
    if not courses:
        html_block(
            """
            <div class="glass-panel">
                <div class="chart-title">No courses returned</div>
                <div class="chart-subtitle">The backend completed the request, but the response did not include any course results.</div>
            </div>
            """
        )
        return

    for index, course in enumerate(courses, start=1):
        metadata = course.get("metadata", {}) if isinstance(course, dict) else {}
        skills_text = metadata.get("skills_text", "") if isinstance(metadata, dict) else ""
        level = metadata.get("level", "") if isinstance(metadata, dict) else ""
        course_cols = st.columns([0.15, 0.9, 0.55, 0.55])
        with course_cols[0]:
            html_block(f"<div class='glass-panel' style='padding: 1rem; text-align:center;'><div class='chart-title' style='margin:0;'>{index:02d}</div></div>")
        with course_cols[1]:
            html_block(
                f"""
                <div class="glass-panel">
                    <div class="chart-title">{esc(course.get('title', 'Untitled Course'))}</div>
                    <div class="chart-subtitle">{esc(course.get('organization', 'Unknown provider'))}</div>
                    <div class="helper-text">{esc(skills_text or 'No skill metadata available.')}</div>
                </div>
                """
            )
        with course_cols[2]:
            html_block(
                f"""
                <div class="glass-panel">
                    <div class="chart-title">Score</div>
                    <div class="subtitle" style="margin:0; color: var(--text-primary);">{float(course.get('score', 0.0)):.2f}</div>
                    <div class="helper-text">{esc(level or 'Metadata-ready')}</div>
                </div>
                """
            )
        with course_cols[3]:
            html_block(f"<div class='glass-panel'><div class='chart-title'>Course ID</div><div class='helper-text'>{esc(course.get('course_id', 'n/a'))}</div></div>")


def render_skill_gaps(response: dict[str, object]) -> None:
    skill_gaps = response.get("skill_gaps", []) or []
    html_block('<div class="section-label">Skill Gap Analysis</div>')
    if not skill_gaps:
        html_block(
            """
            <div class="glass-panel">
                <div class="chart-title">No skill gaps returned</div>
                <div class="chart-subtitle">The backend did not surface any missing skills for this run.</div>
            </div>
            """
        )
        return

    items = []
    for gap in skill_gaps:
        if isinstance(gap, dict):
            title = gap.get("skill", gap.get("missing_skill", "Skill"))
            status = gap.get("status", gap.get("severity", "Review"))
            details = gap.get("details", gap.get("reason", ""))
            items.append(f"<li><strong>{esc(title)}</strong> <span style='color:var(--text-secondary);'>({esc(status)})</span> - {esc(details)}</li>")
    html_block(f"<div class='glass-panel'><ul class='helper-text'>{''.join(items)}</ul></div>")


def render_learning_path(response: dict[str, object]) -> None:
    learning_path = response.get("learning_path") or {}
    html_block('<div class="section-label">Learning Path</div>')
    if not learning_path:
        html_block(
            """
            <div class="glass-panel">
                <div class="chart-title">No learning path returned</div>
                <div class="chart-subtitle">The backend response did not include a path plan.</div>
            </div>
            """
        )
        return

    total_courses = learning_path.get("total_courses", 0)
    stages = learning_path.get("stages", []) or []
    html_block(
        f"""
        <div class="glass-panel">
            <div class="chart-title">Path Summary</div>
            <div class="chart-subtitle">{esc(total_courses)} total courses across {len(stages)} stage(s).</div>
        </div>
        """
    )
    for stage in stages:
        stage_name = stage.get("stage_name", stage.get("name", "Stage")) if isinstance(stage, dict) else "Stage"
        courses = stage.get("courses", []) if isinstance(stage, dict) else []
        html_block(f"<div style='height:0.7rem'></div><div class='glass-panel'><div class='chart-title'>{esc(stage_name)}</div><div class='helper-text'>{len(courses)} course(s)</div></div>")


def render_guardrails(response: dict[str, object]) -> None:
    guardrails = response.get("guardrails") or {}
    html_block('<div class="section-label">Guardrails</div>')
    if not guardrails:
        html_block(
            """
            <div class="glass-panel">
                <div class="chart-title">No guardrail report returned</div>
                <div class="chart-subtitle">The backend response did not include guardrail output.</div>
            </div>
            """
        )
        return

    passed = guardrails.get("passed", guardrails.get("status", ""))
    issues = guardrails.get("issues", []) or []
    html_block(
        f"""
        <div class="glass-panel">
            <div class="chart-title">Validation Status</div>
            <div class="chart-subtitle">{esc('Pass' if passed in (True, 'pass', 'passed', 'ok') else 'Review')}</div>
            <div class="helper-text">{len(issues)} issue(s) detected by the backend validator.</div>
        </div>
        """
    )
    if issues:
        rows = []
        for issue in issues:
            if isinstance(issue, dict):
                rows.append(
                    f"<li><strong>{esc(issue.get('check_name', 'check'))}</strong> - {esc(issue.get('message', issue.get('detail', '')))}"
                    f" <span style='color:var(--text-secondary);'>[{esc(issue.get('severity', 'info'))}]</span></li>"
                )
        html_block(f"<div style='height:0.7rem'></div><div class='glass-panel'><ul class='helper-text'>{''.join(rows)}</ul></div>")


def render_final_response(response: dict[str, object]) -> None:
    html_block('<div class="section-label">Advisor Response</div>')
    html_block(
        f"""
        <div class="glass-panel">
            <div class="chart-title">Full response</div>
            <div class="chart-subtitle">Rendered verbatim from the backend, preserving the orchestration summary.</div>
            <div class="helper-text" style="white-space:pre-wrap;">{esc(response.get('final_response', ''))}</div>
        </div>
        """
    )


def main() -> None:
    st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="wide", initial_sidebar_state="expanded")
    ensure_state()
    inject_styles()

    with st.sidebar:
        html_block(
            """
            <div class="glass-panel">
                <div class="chart-title">Control Sidebar</div>
                <div class="chart-subtitle">Backend connection status and quick helpers.</div>
                <div class="helper-text">The Streamlit client posts directly to the FastAPI service configured in frontend/config.py.</div>
            </div>
            """
        )
        if st.button("Refresh backend status", use_container_width=True):
            st.session_state["last_refresh"] = datetime.now(timezone.utc)
        html_block(
            f"""
            <div style="height:0.9rem"></div>
            <div class="glass-panel">
                <div class="chart-title">Runtime State</div>
                <div class="helper-text">Last refresh: {esc(format_timestamp(st.session_state['last_refresh']))}<br/>API base: {esc(API_BASE_URL)}</div>
            </div>
            """
        )

    render_header()
    html_block('<div style="height:1rem"></div>')

    controls = render_controls()

    if controls["submitted"]:
        st.session_state["query"] = controls["query"]
        st.session_state["skills_raw"] = controls["skills_raw"]
        st.session_state["career_goal"] = controls["career_goal"]
        st.session_state["candidate_k"] = controls["candidate_k"]
        st.session_state["top_k"] = controls["top_k"]
        st.session_state["max_path_courses"] = controls["max_path_courses"]
        st.session_state["use_reranker"] = controls["use_reranker"]

        payload = {
            "query": controls["query"],
            "current_skills": parse_skills(controls["skills_raw"]),
            "career_goal": controls["career_goal"] or controls["query"],
            "candidate_k": int(controls["candidate_k"]),
            "top_k": int(controls["top_k"]),
            "max_path_courses": int(controls["max_path_courses"]),
            "use_reranker": bool(controls["use_reranker"]),
        }

        with st.spinner("Running the backend recommendation graph..."):
            try:
                st.session_state["last_response"] = get_recommendations(payload)
                st.session_state["last_error"] = ""
                st.session_state["last_refresh"] = datetime.now(timezone.utc)
            except ApiClientError as exc:
                st.session_state["last_response"] = None
                st.session_state["last_error"] = str(exc)

    if st.session_state["last_error"]:
        st.error(st.session_state["last_error"])

    response = st.session_state["last_response"]
    if not response:
        render_empty_state()
        return

    render_metrics(response)
    render_courses(response)
    render_skill_gaps(response)
    render_learning_path(response)
    render_guardrails(response)
    render_final_response(response)


if __name__ == "__main__":
    main()