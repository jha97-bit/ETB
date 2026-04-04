"""
Mock Interview AI - User-Friendly Web App
Run with: streamlit run app.py

Set API_URL in the environment when the API is not on localhost (e.g. cloud deploy).
"""

import json
import os
import re
import time

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

try:
    from streamlit_javascript import st_javascript
except ImportError:
    st_javascript = None

API_URL = os.environ.get("API_URL", "http://localhost:8000").rstrip("/")


def _is_local_api_url() -> bool:
    return "localhost" in API_URL or "127.0.0.1" in API_URL


def check_api() -> bool:
    """Ping API root; allow time for cold start on free cloud hosts (Render, etc.)."""
    url = f"{API_URL}/"
    timeout = float(
        os.environ.get(
            "API_CHECK_TIMEOUT",
            "5" if _is_local_api_url() else "45",
        )
    )
    attempts = int(os.environ.get("API_CHECK_ATTEMPTS", "3"))
    pause = float(os.environ.get("API_CHECK_PAUSE", "5"))
    for attempt in range(attempts):
        try:
            r = requests.get(url, timeout=timeout)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        if attempt < attempts - 1:
            time.sleep(pause)
    return False

# Minimal iframe shell: your UI can call parent.postMessage({ type: 'interview_results', data: {...} }, '*')
_EMBED_HTML = """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"/><style>body{margin:0;font-family:ui-sans-serif,system-ui,sans-serif;}</style></head>
<body>
<div style="padding:14px 16px;background:linear-gradient(180deg,#fafbfc 0%,#f1f5f9 100%);border:1px solid #e2e8f0;border-radius:10px;">
  <p style="margin:0 0 6px;font-size:13px;font-weight:700;color:#0f172a;letter-spacing:-0.02em;">Embedded interview HTML</p>
  <p style="margin:0 0 10px;font-size:12px;color:#64748b;line-height:1.5;">
    Replace this markup with your own experience. To sync results into Streamlit, post a message to the parent window:
  </p>
  <pre style="font-size:11px;line-height:1.45;background:#fff;padding:10px 12px;border-radius:8px;border:1px solid #e2e8f0;overflow:auto;margin:0;">
parent.postMessage({{
  type: 'interview_results',
  data: {{
    overallScore: 4,
    maxScore: 5,
    answeredCount: 3,
    averageScore: 80,
    questions: [{{ questionIndex: 1, question: '…', answerPreview: '…' }}]
  }}
}}, '*');</pre>
</div>
</body>
</html>
""".replace("{{", "{").replace("}}", "}")

# Sidebar: display title (caps) + helper description (shown below selection)
MODE_META = {
    "behavioral": {
        "title": "BEHAVIORAL",
        "desc": "Leadership, collaboration, ownership, and reflecting on past experience.",
    },
    "technical": {
        "title": "TECHNICAL",
        "desc": "Concepts, systems, implementation trade-offs, and technical depth.",
    },
    "case": {
        "title": "CASE STUDY",
        "desc": "Business analytics, product sense, data, and structured problem-solving.",
    },
}


def _answer_template_markdown(mode: str) -> str:
    """Bullet structure to guide answers (shown as a template in the UI)."""
    if mode == "behavioral":
        return (
            "- **Situation** — brief context (team, stakes, constraints)\n"
            "- **Task** — what you were asked to do or own\n"
            "- **Action** — what *you* did (specific steps, tools, people)\n"
            "- **Result** — outcome with numbers or learning if possible"
        )
    if mode == "technical":
        return (
            "- **Clarify** — requirements, scale, constraints, assumptions\n"
            "- **Approach** — main design or solution path (2–3 options if useful)\n"
            "- **Trade-offs** — pros/cons and what you’d pick\n"
            "- **Risks / next steps** — failure modes, testing, monitoring"
        )
    # case study
    return (
        "- **Frame** — goal, stakeholder, success metric, constraints\n"
        "- **Hypotheses** — 2–3 plausible drivers; how you’d test them\n"
        "- **Analysis** — data, segments, metrics, or simple quant where relevant\n"
        "- **Recommendation** — decision, trade-offs, risks, and what you’d do next"
    )


def _request_error_message(e: Exception) -> str:
    """Prefer FastAPI `detail` when a request fails (e.g. 400 guardrails)."""
    resp = getattr(e, "response", None)
    if resp is not None:
        try:
            data = resp.json()
            if isinstance(data, dict) and data.get("detail"):
                return str(data["detail"])
        except Exception:
            pass
    return str(e)


def _summary_to_html(text: str) -> str:
    """Convert markdown-style bold (**text**) to HTML for styled display."""
    if not text:
        return ""
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)


def _html_escape(s: str) -> str:
    if not s:
        return ""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _api_session_id(mode: str) -> str:
    """Separate orchestrator question-bank state per interview type."""
    return f"web-{mode}"


def _clear_interview_progress() -> None:
    """Reset active interview (used by Start Over and when interview type changes)."""
    st.session_state.questions = []
    st.session_state.answers = []
    st.session_state.current_question = None
    st.session_state.current_hint = None
    st.session_state.started = False
    st.session_state.latest_feedback = None
    st.session_state.interview_results = None
    st.session_state.highlight_answer_for_new_question = False
    st.session_state.show_new_question_toast = False
    st.session_state.expand_answer_template = False
    if "_last_embed_hash" in st.session_state:
        del st.session_state["_last_embed_hash"]


def _build_interview_results_payload(mode: str) -> dict:
    """Session snapshot for metrics, DataFrame, and JSON export (camelCase for embed/postMessage)."""
    fb = st.session_state.get("latest_feedback")
    qs = list(st.session_state.get("questions") or [])
    ans = list(st.session_state.get("answers") or [])
    answered_count = len(ans)
    max_score = int(fb["max_score"]) if fb and fb.get("max_score") is not None else None
    overall = fb.get("overall_score") if fb else None
    if overall is not None and max_score and max_score > 0:
        avg_pct = round(100.0 * float(overall) / float(max_score), 1)
    else:
        avg_pct = None
    rows = []
    for i, q in enumerate(qs):
        a = ans[i] if i < len(ans) else ""
        rows.append(
            {
                "questionIndex": i + 1,
                "question": (q[:800] + "…") if len(q) > 800 else q,
                "answerPreview": (a[:400] + "…") if len(a) > 400 else a,
            }
        )
    return {
        "overallScore": overall,
        "maxScore": max_score,
        "overallScoreLabel": f"{overall} / {max_score}" if overall is not None and max_score is not None else "—",
        "answeredCount": answered_count,
        "averageScore": avg_pct,
        "averageScoreLabel": f"{avg_pct}%" if avg_pct is not None else "—",
        "questions": rows,
        "timestamp": int(time.time()),
        "mode": mode,
        "rawFeedback": fb,
    }


def _merge_embed_results(base: dict, embed) -> dict:
    """Overlay postMessage payload from embedded HTML (same shape as base or partial)."""
    if not embed or not isinstance(embed, dict):
        return base
    merged = {**base, **embed}
    if "questions" not in merged or not merged["questions"]:
        merged["questions"] = base.get("questions") or []
    return merged


def _normalize_js_payload(raw):
    """st_javascript may return a dict or a JSON string."""
    if raw is None or raw is False:
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    return None


def _render_interview_results_dashboard() -> None:
    """Metrics + table + JSON download (theme aligned with embedded postMessage schema)."""
    r = st.session_state.get("interview_results")
    if not r or not isinstance(r, dict):
        return
    has_rows = bool(r.get("questions"))
    has_feedback = bool(r.get("rawFeedback"))
    if not has_rows and not has_feedback and r.get("answeredCount", 0) == 0:
        return

    st.markdown("---")
    st.subheader("Interview results")
    col1, col2, col3 = st.columns(3)
    with col1:
        ov = r.get("overallScoreLabel")
        if ov is None and r.get("overallScore") is not None:
            ov = str(r.get("overallScore"))
        st.metric("Overall score", ov if ov is not None else "—")
    with col2:
        st.metric("Questions answered", r.get("answeredCount", 0))
    with col3:
        av = r.get("averageScoreLabel")
        if av is None and r.get("averageScore") is not None:
            av = str(r.get("averageScore"))
        st.metric("Average score", av if av is not None else "—")

    st.caption("Question-wise activity (previews may be truncated).")
    df = pd.DataFrame(r.get("questions") or [])
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.caption("No question rows yet—answer in the main flow or post results from the embedded HTML.")

    ts = r.get("timestamp") or int(time.time())
    st.download_button(
        label="Download results as JSON",
        data=json.dumps(r, indent=2, default=str),
        file_name=f"interview_results_{ts}.json",
        mime="application/json",
        key="download_interview_json",
    )


# Page config
st.set_page_config(
    page_title="Mock Interview Platform",
    page_icon="🎤",
    layout="wide",
)

# Custom styling — professional layout, sidebar interview types (caps + small desc)
st.markdown("""
<style>
    :root {
        --bg-primary: #f4f6f9;
        --bg-surface: #ffffff;
        --bg-surface-2: #eef2ff;
        --text-primary: #0f172a;
        --text-secondary: #475569;
        --text-muted: #64748b;
        --accent: #1d4ed8;
        --accent-2: #5b21b6;
        --success: #15803d;
        --warning: #c2410c;
        --border-subtle: #e2e8f0;
    }
    html, body, [class*="css"] {
        font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
    }
    .main h3 {
        font-size: 1.05rem;
        font-weight: 600;
        letter-spacing: -0.02em;
        color: #1e293b;
        margin-top: 0.5rem;
    }
    .stApp {
        background: linear-gradient(165deg, #f8fafc 0%, #eef2f7 45%, #f1f5f9 100%);
        color: var(--text-primary);
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #fafbfc 0%, #f4f6f9 100%);
        border-right: 1px solid var(--border-subtle);
        box-shadow: 4px 0 24px rgba(15, 23, 42, 0.04);
    }
    .stMarkdown, p, label {
        color: var(--text-primary);
    }
    .app-hero-title {
        font-size: 1.85rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        color: #0f172a;
        margin: 0 0 0.35rem 0;
        line-height: 1.2;
    }
    .app-hero-sub {
        font-size: 0.95rem;
        font-weight: 400;
        color: var(--text-muted);
        line-height: 1.55;
        margin: 0 0 0.25rem 0;
        max-width: 52rem;
    }
    .sidebar-panel-title {
        font-size: 0.6875rem;
        font-weight: 700;
        letter-spacing: 0.14em;
        color: var(--text-muted);
        margin: 0 0 1rem 0;
        text-transform: uppercase;
    }
    .sidebar-section-label {
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.16em;
        color: #94a3b8;
        margin: 0 0 0.45rem 0;
        text-transform: uppercase;
    }
    .mode-type-desc {
        font-size: 0.8125rem;
        color: var(--text-secondary);
        line-height: 1.5;
        margin: -0.2rem 0 1.15rem 0;
        padding: 0 0.1rem 0 0.15rem;
        font-weight: 400;
        border-left: 2px solid #cbd5e1;
        padding-left: 0.65rem;
    }
    .big-font { font-size: 24px !important; font-weight: 600; }
    .interview-flow {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        margin: 0 0 1.5rem 0;
        max-width: 100%;
    }
    .card-label {
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.14em;
        color: #94a3b8;
        text-transform: uppercase;
        margin: 0 0 0.4rem 0.15rem;
    }
    .question-box {
        background: linear-gradient(160deg, #e8f1ff 0%, #dbeafe 50%, #cfe8fd 100%);
        color: var(--text-primary);
        padding: 1.25rem 1.35rem 1.35rem 1.35rem;
        border-radius: 12px;
        margin: 0;
        border: 1px solid rgba(59, 130, 246, 0.22);
        border-left: 5px solid #2563eb;
        box-shadow: 0 4px 16px rgba(37, 99, 235, 0.1);
        font-size: 1.05rem;
        line-height: 1.65;
        width: 100%;
        max-width: 100%;
    }
    .scenario-box {
        background: #ffffff;
        color: #334155;
        padding: 1.15rem 1.35rem;
        border-radius: 12px;
        margin: 0;
        border: 1px solid #e8e5ff;
        border-left: 5px solid #7c3aed;
        box-shadow: 0 4px 14px rgba(124, 58, 237, 0.08);
        line-height: 1.6;
        font-size: 0.98rem;
    }
    .scenario-box .scenario-lead {
        font-weight: 700;
        color: #5b21b6;
        margin-right: 0.35rem;
    }
    .answer-workspace {
        background: #ffffff;
        border: 1px solid var(--border-subtle);
        border-radius: 14px;
        padding: 1rem 1.2rem 1rem;
        margin: 0.35rem 0 0.85rem 0;
        box-shadow: 0 2px 12px rgba(15, 23, 42, 0.05);
    }
    .answer-workspace-title {
        font-size: 1.02rem;
        font-weight: 700;
        color: #1e293b;
        margin: 0;
        letter-spacing: -0.02em;
        padding-bottom: 0.6rem;
        border-bottom: 1px solid #f1f5f9;
    }
    .answer-workspace .new-question-banner {
        margin-top: 0.75rem;
    }
    .answer-box {
        background-color: #e8f7ee;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .feedback-box {
        background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%);
        color: #1f2937;
        padding: 1.75rem 2.5rem;
        border-radius: 12px;
        margin: 1.25rem 0;
        border-left: 5px solid var(--warning);
        width: 100%;
        max-width: 100%;
        line-height: 1.8;
        font-size: 1.05rem;
        box-sizing: border-box;
        display: block;
        box-shadow: 0 10px 22px rgba(217, 119, 6, 0.14);
    }
    .feedback-box strong { color: #b45309; }
    .dimension-item {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        color: #1f2937;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        margin: 0.75rem 0;
        border-left: 3px solid var(--accent);
        width: 100%;
        line-height: 1.6;
        box-shadow: 0 8px 16px rgba(2, 6, 23, 0.08);
    }
    .dimension-item strong { color: #1d4ed8; }
    /* Desktop layout: use horizontal space */
    .main .block-container {
        max-width: 100%;
        padding: 2rem 3rem;
    }
    @media (min-width: 768px) {
        .main .block-container { max-width: 1100px; }
    }
    @media (min-width: 1200px) {
        .main .block-container { max-width: 1400px; }
    }
    .success-msg { color: var(--success); }
    .step { 
        background: #f1f5f9; 
        padding: 0.5rem 1rem; 
        border-radius: 8px; 
        margin: 0.3rem 0;
        font-size: 14px;
        border: 1px solid #d1d9e6;
    }
    .header-ribbon {
        height: 12px;
        width: 100%;
        border-radius: 999px;
        margin: 0.4rem 0 1.1rem 0;
        background: linear-gradient(90deg, #38bdf8 0%, #60a5fa 35%, #a78bfa 70%, #f59e0b 100%);
        box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.12) inset, 0 6px 18px rgba(59, 130, 246, 0.25);
    }
    /* Sidebar interview type: bold caps labels */
    section[data-testid="stSidebar"] div[role="radiogroup"] > label {
        background: #ffffff;
        border: 1px solid var(--border-subtle);
        border-left: 3px solid #3b82f6;
        border-radius: 8px;
        padding: 0.55rem 0.7rem;
        margin-bottom: 0.4rem;
        transition: border-color 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
        border-color: #93c5fd;
        background: #f8fafc;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label > div {
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        line-height: 1.35;
        color: #0f172a !important;
        text-transform: uppercase;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label * {
        color: #0f172a !important;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
        background: linear-gradient(135deg, #eff6ff 0%, #f5f3ff 100%);
        border-color: #93c5fd;
        border-left-color: #2563eb;
        box-shadow: 0 1px 0 rgba(255,255,255,0.8) inset, 0 6px 16px rgba(37, 99, 235, 0.12);
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) > div,
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) * {
        color: #1e3a8a !important;
    }
    /* Button styling */
    .stButton > button {
        border-radius: 8px;
        border: 1px solid #c7d2fe;
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        color: #1e293b;
        font-weight: 600;
        font-size: 0.9rem;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
    }
    .stButton > button:hover {
        border-color: #6366f1;
        background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
        color: #0f172a;
    }
    div[data-testid="stButton"] button[kind="primary"] {
        background: linear-gradient(135deg, #2563eb 0%, #4f46e5 100%) !important;
        color: #ffffff !important;
        border: 1px solid #1d4ed8 !important;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35);
    }
    div[data-testid="stButton"] button[kind="primary"]:hover {
        background: linear-gradient(135deg, #1d4ed8 0%, #4338ca 100%) !important;
    }
    /* Inputs for better contrast */
    .stTextArea textarea {
        background: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #d1d9e6 !important;
        border-radius: 10px !important;
    }
    .new-question-banner {
        background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
        border: 1px solid #ddd6fe;
        border-radius: 10px;
        padding: 0.65rem 0.95rem;
        margin: 0 0 0.85rem 0;
        color: #4c1d95;
        font-size: 0.88rem;
        font-weight: 500;
        line-height: 1.45;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown(
    """
    <div class="header-ribbon"></div>
    <p class="app-hero-title">Mock Interview Platform</p>
    <p class="app-hero-sub">
        Practice realistic interview questions, respond in your own words, and get structured feedback
        on clarity, depth, and structure—before the real conversation.
    </p>
    """,
    unsafe_allow_html=True,
)
st.markdown("---")

# Check API once per session (retries help when free-tier API is waking from sleep)
if "api_ok" not in st.session_state:
    st.session_state.api_ok = False

if not st.session_state.api_ok:
    if check_api():
        st.session_state.api_ok = True
    else:
        st.error("⚠️ **The API is not reachable** from this app.")
        if _is_local_api_url():
            st.code("python main.py", language="bash")
            st.info("Open a terminal, go to your project folder, and run the command above. Then refresh this page.")
        else:
            st.info(
                f"**API_URL** is `{API_URL}`. On **free** hosting the API often **sleeps**; loading can take "
                "**30–60+ seconds**. Open your API link in another tab first, wait until you see JSON, then "
                "click **Try again** below."
            )
            st.caption(
                "Render: **Streamlit** service → **Environment** → `API_URL` = your API URL (https, no trailing slash)."
            )
        if st.button("Try again"):
            st.rerun()
        st.stop()

# Sidebar — interview type (caps/bold via CSS) + smaller description
st.sidebar.markdown(
    '<p class="sidebar-panel-title">Settings</p>',
    unsafe_allow_html=True,
)
st.sidebar.markdown(
    '<p class="sidebar-section-label">Interview type</p>',
    unsafe_allow_html=True,
)
mode = st.sidebar.radio(
    "Interview type",
    ["behavioral", "technical", "case"],
    format_func=lambda x: MODE_META[x]["title"],
    label_visibility="collapsed",
    key="interview_mode",
)
st.sidebar.markdown(
    f'<p class="mode-type-desc">{MODE_META[mode]["desc"]}</p>',
    unsafe_allow_html=True,
)

# Initialize session state
if "questions" not in st.session_state:
    st.session_state.questions = []
if "answers" not in st.session_state:
    st.session_state.answers = []
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "current_hint" not in st.session_state:
    st.session_state.current_hint = None
if "started" not in st.session_state:
    st.session_state.started = False
if "latest_feedback" not in st.session_state:
    st.session_state.latest_feedback = None
if "highlight_answer_for_new_question" not in st.session_state:
    st.session_state.highlight_answer_for_new_question = False
if "show_new_question_toast" not in st.session_state:
    st.session_state.show_new_question_toast = False
if "expand_answer_template" not in st.session_state:
    st.session_state.expand_answer_template = False
if "interview_results" not in st.session_state:
    st.session_state.interview_results = None
if "last_interview_mode" not in st.session_state:
    st.session_state.last_interview_mode = mode

# If user changes interview type during an active session, reset so questions match the selection.
if st.session_state.get("started") and mode != st.session_state.last_interview_mode:
    _clear_interview_progress()
    st.session_state.last_interview_mode = mode
    st.info(
        f"Interview type changed — previous progress was cleared. Click **Start Interview** to begin a "
        f"**{MODE_META[mode]['title']}** session."
    )
    st.rerun()

st.session_state.last_interview_mode = mode

# Optional: iframe → parent.postMessage → Streamlit (streamlit-javascript)
result_data = None
if st_javascript is not None:
    try:
        _raw_js = st_javascript(
            """
            (function() {
              if (!window.__etbInterviewMsg) {
                window.__etbInterviewMsg = true;
                window.interview_results = window.interview_results || null;
                window.addEventListener('message', function(event) {
                  try {
                    if (event.data && event.data.type === 'interview_results') {
                      window.interview_results = event.data.data;
                    }
                  } catch (e) {}
                });
              }
              return window.interview_results;
            })();
            """
        )
        result_data = _normalize_js_payload(_raw_js)
    except Exception:
        result_data = None

_base_results = _build_interview_results_payload(mode)
if result_data:
    st.session_state.interview_results = _merge_embed_results(_base_results, result_data)
    _h = hash(json.dumps(result_data, sort_keys=True, default=str))
    if st.session_state.get("_last_embed_hash") != _h:
        st.session_state._last_embed_hash = _h
        if hasattr(st, "toast"):
            st.toast("Embedded view posted interview results.", icon="📥")
        else:
            st.success("Results received from embedded view (postMessage).")
else:
    st.session_state.interview_results = _base_results

with st.expander("Embedded HTML interview (optional)", expanded=False):
    st.caption(
        "Runs in an iframe below. From your HTML/JS, call **parent.postMessage** with "
        "`type: 'interview_results'` and `data` matching the session export shape."
    )
    components.html(_EMBED_HTML, height=340, scrolling=True)

# Main flow
if not st.session_state.started:
    st.subheader("Get Started")
    st.markdown("""
    1. **Click "Start Interview"** below to get your first question.
    2. **Read the question** and think about your answer.
    3. **Type your answer** in the text box and submit.
    4. You'll get a follow-up question, or you can **evaluate** your answer for feedback.
    """)
    
    if st.button("🚀 Start Interview", type="primary", use_container_width=True):
        try:
            r = requests.post(
                f"{API_URL}/ask_question",
                json={
                    "session_id": _api_session_id(mode),
                    "user_id": "user",
                    "mode": mode,
                },
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
            st.session_state.current_question = data["question"]
            st.session_state.current_hint = data.get("hint")
            st.session_state.questions.append(data["question"])
            st.session_state.started = True
            st.session_state.highlight_answer_for_new_question = True
            st.session_state.show_new_question_toast = True
            st.rerun()
        except Exception as e:
            st.error(f"Could not get question: {_request_error_message(e)}")

else:
    # Toast / banner when a new question just loaded (persists across rerun; success before rerun does not)
    if st.session_state.get("show_new_question_toast"):
        if hasattr(st, "toast"):
            st.toast("New question — answer below. Your previous response was saved.", icon="✨")
        st.session_state.show_new_question_toast = False

    # Current round: question → context → answer (single stacked flow)
    _q_text = _html_escape(st.session_state.current_question or "")
    _flow_parts = [
        '<div class="interview-flow">',
        '<div><div class="card-label">Question</div>',
        f'<div class="question-box">{_q_text}</div></div>',
    ]
    if st.session_state.current_hint:
        _h = (st.session_state.current_hint or "").strip()
        _h_lower = _h.lower()
        if _h_lower.startswith("scenario"):
            _scenario_html = f'<div class="scenario-box">{_html_escape(_h)}</div>'
        else:
            _scenario_html = (
                '<div class="scenario-box"><span class="scenario-lead">Scenario</span> '
                f"{_html_escape(_h)}</div>"
            )
        _flow_parts.append('<div><div class="card-label">Context</div>')
        _flow_parts.append(_scenario_html)
        _flow_parts.append("</div>")
    _flow_parts.append("</div>")
    st.markdown("".join(_flow_parts), unsafe_allow_html=True)

    _ans_header = ['<div class="answer-workspace">', '<div class="answer-workspace-title">✍️ Your answer</div>']
    if st.session_state.get("highlight_answer_for_new_question"):
        _ans_header.append(
            '<div class="new-question-banner">✨ <strong>New question</strong> — type your answer below '
            "(the box is highlighted until you submit).</div>"
        )
    _ans_header.append("</div>")
    st.markdown("".join(_ans_header), unsafe_allow_html=True)
    if st.session_state.get("highlight_answer_for_new_question"):
        st.markdown(
            """
<style>
section.main .stTextArea textarea {
    background: #faf5ff !important;
    border: 2px solid #a855f7 !important;
    box-shadow: 0 0 0 3px rgba(168, 85, 247, 0.12) !important;
    border-radius: 10px !important;
}
</style>
""",
            unsafe_allow_html=True,
        )
    _expand_tpl = st.session_state.pop("expand_answer_template", False)
    with st.expander(
        "Answer structure (template)",
        expanded=bool(_expand_tpl),
    ):
        st.markdown(_answer_template_markdown(mode))
    _q_key = f"answer_q_{len(st.session_state.questions)}"
    answer = st.text_area(
        "Type your response here (as you would say it in a real interview):",
        height=160,
        placeholder="Type your answer here…",
        label_visibility="collapsed",
        key=_q_key,
    )
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("➡️ Submit & Get Next Question", use_container_width=True):
            if not answer.strip():
                st.warning("Please type an answer first.")
            else:
                try:
                    st.session_state.highlight_answer_for_new_question = False
                    st.session_state.answers.append(answer)
                    r = requests.post(
                        f"{API_URL}/ask_question",
                        json={
                            "session_id": _api_session_id(mode),
                            "user_id": "user",
                            "mode": mode,
                            "last_question": st.session_state.current_question,
                            "last_answer": answer,
                        },
                        timeout=15,
                    )
                    r.raise_for_status()
                    data = r.json()
                    st.session_state.current_question = data["question"]
                    st.session_state.current_hint = data.get("hint")
                    st.session_state.questions.append(data["question"])
                    st.session_state.highlight_answer_for_new_question = True
                    st.session_state.show_new_question_toast = True
                    st.session_state.expand_answer_template = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {_request_error_message(e)}")
    
    with col2:
        if st.button("📊 Get Feedback on My Answer", use_container_width=True):
            if not answer.strip():
                st.warning("Please type an answer first.")
            else:
                with st.spinner("Evaluating your response..."):
                    try:
                        r = requests.post(
                            f"{API_URL}/evaluate",
                            json={
                                "question": st.session_state.current_question,
                                "answer": answer,
                                "mode": mode,
                            },
                            timeout=30,
                        )
                        r.raise_for_status()
                        data = r.json()
                        st.session_state.latest_feedback = data
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not get feedback: {e}")
    
    st.markdown("---")

    if st.session_state.latest_feedback:
        data = st.session_state.latest_feedback
        st.subheader("📊 Your Feedback")
        row1_col1, row1_col2 = st.columns([1, 3])
        with row1_col1:
            st.metric("Overall Score", f"{data['overall_score']} / {data['max_score']}")
        with row1_col2:
            summary_html = _summary_to_html(data.get("summary_feedback", ""))
            st.markdown(
                f'<div class="feedback-box"><strong>Summary</strong><br><br>{summary_html}</div>',
                unsafe_allow_html=True,
            )

        if data.get("growth_tips"):
            st.subheader("💡 Tips to Improve")
            tips_html = "<ul style='line-height: 1.8; font-size: 1rem; max-width: 100%;'>"
            for tip in data["growth_tips"]:
                tip_html = _summary_to_html(tip)
                tips_html += f"<li style='margin-bottom: 0.5rem;'>{tip_html}</li>"
            tips_html += "</ul>"
            st.markdown(tips_html, unsafe_allow_html=True)

        if data.get("dimensions"):
            st.markdown("---")
            st.subheader("📈 Detailed Scores by Category")
            n_dims = len(data["dimensions"])
            # Keep cards readable by avoiding too many columns.
            n_cols = 2 if n_dims >= 2 else 1
            dim_cols = st.columns(n_cols)
            for idx, d in enumerate(data["dimensions"]):
                with dim_cols[idx % n_cols]:
                    dimension_html = _summary_to_html(f"**{d['dimension']}:** {d['score']}/5 - {d['feedback']}")
                    st.markdown(
                        f'<div class="dimension-item">{dimension_html}</div>',
                        unsafe_allow_html=True,
                    )

    # Show Q&A history
    if st.session_state.questions:
        with st.expander("📜 View your interview so far"):
            for i, (q, a) in enumerate(zip(st.session_state.questions, st.session_state.answers), 1):
                st.markdown(f"**Q{i}:** {q}")
                if i <= len(st.session_state.answers):
                    st.markdown(f"*Your answer:* {a}")
                st.markdown("")
    
    if st.sidebar.button("🔄 Start Over"):
        _clear_interview_progress()
        st.rerun()

_render_interview_results_dashboard()
