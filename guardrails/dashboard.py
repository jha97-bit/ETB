"""HITL Dashboard: Streamlit UI for mentor review and take-over."""

import json
from pathlib import Path

try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

# Events file for dashboard to read (writable by API)
EVENTS_FILE = Path(__file__).parent.parent / "data" / "hitl_events.json"


def run_dashboard():
    """Run the Streamlit HITL dashboard."""
    if not HAS_STREAMLIT:
        raise ImportError("Install streamlit: pip install streamlit")

    st.set_page_config(page_title="Mock Interview HITL", layout="wide")
    st.title("Mock Interview – Human-in-the-Loop Dashboard")
    st.caption("Review flagged events and provide mentor feedback.")

    if not EVENTS_FILE.exists():
        EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        EVENTS_FILE.write_text("[]")

    events = json.loads(EVENTS_FILE.read_text())
    if not events:
        st.info("No flagged events yet. Events will appear here when guardrails flag content.")
        return

    for i, evt in enumerate(events):
        with st.expander(f"Session {evt.get('session_id', '?')} – {evt.get('reason', 'Flagged')}", expanded=True):
            st.json(evt)
            mentor_feedback = st.text_area("Mentor feedback", key=f"fb_{i}")
            if st.button("Submit feedback & resolve", key=f"btn_{i}"):
                evt["mentor_feedback"] = mentor_feedback
                evt["resolved"] = True
                events.pop(i)
                EVENTS_FILE.write_text(json.dumps(events, indent=2))
                st.success("Feedback submitted.")
                st.rerun()


if __name__ == "__main__":
    run_dashboard()
