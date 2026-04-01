"""
Mock Interview AI - User-Friendly Web App
Run with: streamlit run app.py
"""

import re
import streamlit as st
import requests

API_URL = "http://localhost:8000"


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

# Page config
st.set_page_config(
    page_title="Mock Interview Practice",
    page_icon="🎤",
    layout="wide",  # Use wide layout for better horizontal space
)

# Custom styling for friendlier look
st.markdown("""
<style>
    :root {
        --bg-primary: #f8fafc;
        --bg-surface: #ffffff;
        --bg-surface-2: #eef2ff;
        --text-primary: #0f172a;
        --text-secondary: #334155;
        --accent: #2563eb;
        --accent-2: #7c3aed;
        --success: #16a34a;
        --warning: #d97706;
    }
    .stApp {
        background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
        color: var(--text-primary);
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
        border-right: 1px solid #dbe3ef;
    }
    .stMarkdown, p, label {
        color: var(--text-primary);
    }
    .big-font { font-size: 24px !important; font-weight: 600; }
    .question-box {
        background: linear-gradient(145deg, #dbeafe 0%, #bfdbfe 100%);
        color: var(--text-primary);
        padding: 1.5rem 2rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 5px solid #3b82f6;
        box-shadow: 0 10px 20px rgba(59, 130, 246, 0.18);
        font-size: 1.1rem;
        line-height: 1.6;
        width: 100%;
        max-width: 100%;
    }
    .scenario-box {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        color: #1f2937;
        padding: 1rem 1.2rem;
        border-radius: 10px;
        margin: 0.5rem 0 1rem 0;
        border-left: 4px solid #7c3aed;
        box-shadow: 0 8px 16px rgba(124, 58, 237, 0.1);
        line-height: 1.5;
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
    /* Make sidebar interview type options more visible */
    section[data-testid="stSidebar"] div[role="radiogroup"] > label {
        background: #ffffff;
        border: 1px solid #d1d9e6;
        border-left: 4px solid var(--accent);
        border-radius: 10px;
        padding: 0.65rem 0.75rem;
        margin-bottom: 0.45rem;
        transition: all 0.2s ease;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
        border-color: #60a5fa;
        background: #f8fbff;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label > div {
        font-size: 0.96rem;
        font-weight: 600;
        line-height: 1.35;
        color: #0f172a !important;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label * {
        color: #0f172a !important;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
        background: #eff6ff;
        border-color: #93c5fd;
        box-shadow: 0 0 0 1px #93c5fd inset, 0 8px 18px rgba(96, 165, 250, 0.15);
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) > div,
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) * {
        color: #0f172a !important;
    }
    /* Button styling */
    .stButton > button {
        border-radius: 10px;
        border: 1px solid #7aa6ff;
        background: linear-gradient(135deg, #dbeafe 0%, #e9d5ff 100%);
        color: #1e1b4b;
        font-weight: 600;
    }
    .stButton > button:hover {
        border-color: #4f46e5;
        background: linear-gradient(135deg, #bfdbfe 0%, #ddd6fe 100%);
        color: #1e1b4b;
    }
    /* Inputs for better contrast */
    .stTextArea textarea {
        background: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #d1d9e6 !important;
        border-radius: 10px !important;
    }
    .new-question-banner {
        background: linear-gradient(90deg, #ede9fe 0%, #e0e7ff 100%);
        border: 1px solid #c4b5fd;
        border-radius: 10px;
        padding: 0.75rem 1rem;
        margin: 0.5rem 0 1rem 0;
        color: #1e1b4b;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("🎤 Mock Interview Practice")
st.markdown('<div class="header-ribbon"></div>', unsafe_allow_html=True)
st.markdown("---")
st.markdown("""
**What this does:** This app conducts a practice interview with you. It asks questions, you answer, 
and it can give you feedback on how well you responded.
""")

# Check if API is running
@st.cache_data(ttl=5)
def check_api():
    try:
        r = requests.get(f"{API_URL}/", timeout=2)
        return True
    except Exception:
        return False

if not check_api():
    st.error("⚠️ **The API server isn't running.** Please start it first:")
    st.code("python main.py", language="bash")
    st.info("Open a terminal, go to your project folder, and run the command above. Then refresh this page.")
    st.stop()

# Sidebar - Mode selection
st.sidebar.header("Interview Settings")
st.sidebar.markdown("### Choose Interview Type")
mode = st.sidebar.radio(
    "Interview Type",
    ["behavioral", "technical", "case"],
    format_func=lambda x: {
        "behavioral": "Behavioral - leadership, collaboration, ownership",
        "technical": "Technical - concepts, systems, implementation",
        "case": "Case Study - business analytics / product / data science",
    }[x],
    label_visibility="collapsed",
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
                json={"session_id": "web-session", "user_id": "user", "mode": mode},
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

    # Show current question
    st.subheader("📋 Your Question")
    st.markdown(f'<div class="question-box">{st.session_state.current_question}</div>', unsafe_allow_html=True)
    if st.session_state.current_hint:
        st.markdown(f'<div class="scenario-box">{st.session_state.current_hint}</div>', unsafe_allow_html=True)
    
    # Answer input
    st.subheader("✍️ Your Answer")
    if st.session_state.get("highlight_answer_for_new_question"):
        st.markdown(
            '<div class="new-question-banner">✨ <strong>New question</strong> — type your answer in the box below '
            "(highlighted until you submit).</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            """
<style>
section.main .stTextArea textarea {
    background: #faf5ff !important;
    border: 2px solid #a855f7 !important;
    box-shadow: 0 0 0 3px rgba(168, 85, 247, 0.15) !important;
}
</style>
""",
            unsafe_allow_html=True,
        )
    _expand_tpl = st.session_state.pop("expand_answer_template", False)
    with st.expander(
        "💡 Answer template (structure)",
        expanded=bool(_expand_tpl),
    ):
        st.markdown(_answer_template_markdown(mode))
    # Unique key per question so the field resets and Streamlit doesn't reuse stale text
    _q_key = f"answer_q_{len(st.session_state.questions)}"
    answer = st.text_area(
        "Type your response here (as you would say it in a real interview):",
        height=150,
        placeholder="Type your answer to the question above…",
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
                            "session_id": "web-session",
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
        st.session_state.questions = []
        st.session_state.answers = []
        st.session_state.current_question = None
        st.session_state.current_hint = None
        st.session_state.started = False
        st.session_state.latest_feedback = None
        st.session_state.highlight_answer_for_new_question = False
        st.session_state.show_new_question_toast = False
        st.rerun()
