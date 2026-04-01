"""Unit tests for Memory service."""

import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.schemas import MemoryEvent, RecallContextRequest
from memory.service import MemoryService


def test_save_and_recall():
    """Save event and recall context."""
    svc = MemoryService()
    evt = MemoryEvent(
        session_id="s1",
        user_id="u1",
        event_type="qa_pair",
        content={"question": "Q1", "answer": "A1"},
    )
    event_id = svc.save_event(evt)
    assert event_id

    req = RecallContextRequest(session_id="s1", user_id="u1", limit=5)
    resp = svc.recall_context(req)
    assert len(resp.events) >= 1
    assert resp.events[0].content.get("question") == "Q1"
