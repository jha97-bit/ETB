"""Unit tests for Orchestrator ( mocked memories )."""

import pytest
from unittest.mock import MagicMock

# Ensure project root in path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.schemas import AskQuestionRequest, InterviewMode
from orchestrator.agent import OrchestratorAgent


def test_ask_first_question():
    """First question returns a non-empty string from question bank."""
    agent = OrchestratorAgent()
    req = AskQuestionRequest(session_id="t1", user_id="u1", mode=InterviewMode.BEHAVIORAL)
    resp = agent.ask_question(req)
    assert resp.question
    assert len(resp.question) > 10
    assert resp.mode == InterviewMode.BEHAVIORAL
    assert resp.session_id == "t1"
    assert resp.is_followup is False


def test_ask_followup_without_llm():
    """Without LLM, follow-up falls back to question bank."""
    agent = OrchestratorAgent()
    agent._llm = None  # Simulate no API key
    req = AskQuestionRequest(
        session_id="t2",
        user_id="u1",
        mode=InterviewMode.TECHNICAL,
        last_question="How would you design a URL shortener?",
        last_answer="I would use a hash table and base62 encoding.",
    )
    resp = agent.ask_question(req)
    assert resp.question
    assert resp.is_followup is True
