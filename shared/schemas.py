"""Shared Pydantic schemas for the Mock Interview AI system."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class InterviewMode(str, Enum):
    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"
    CASE = "case"
    TESTCASES = "testcases"


class QAPair(BaseModel):
    """A question-answer pair from the interview."""

    question: str
    answer: str
    mode: Optional[InterviewMode] = None


class AskQuestionRequest(BaseModel):
    """Request to get the next interview question."""

    session_id: str
    user_id: str
    mode: InterviewMode = InterviewMode.BEHAVIORAL
    last_answer: Optional[str] = None
    last_question: Optional[str] = None
    target_role: Optional[str] = None
    conversation_history: Optional[list[QAPair]] = None
    case_title: Optional[str] = None
    case_context: Optional[str] = None


class AskQuestionResponse(BaseModel):
    """Response with the next interview question."""

    question: str
    mode: InterviewMode
    is_followup: bool = False
    session_id: str
    hint: Optional[str] = None


class MemoryEvent(BaseModel):
    """Event to store in memory."""

    session_id: str
    user_id: str
    event_type: str = Field(..., description="e.g., qa_pair, evaluation, skill_gap")
    content: dict[str, Any]
    metadata: Optional[dict[str, Any]] = None


class RecallContextRequest(BaseModel):
    """Request to recall context from memory."""

    session_id: str
    user_id: str
    query: Optional[str] = None
    limit: int = 10
    event_types: Optional[list[str]] = None


class RecallContextResponse(BaseModel):
    """Context recalled from memory."""

    events: list[MemoryEvent]
    summary: Optional[str] = None
    weak_skills: Optional[list[str]] = None


class EvaluateResponseRequest(BaseModel):
    """Request to evaluate a user response."""

    question: str
    answer: str
    mode: InterviewMode = InterviewMode.BEHAVIORAL
    target_role: Optional[str] = None
    rubric_id: Optional[str] = None


class DimensionScore(BaseModel):
    """Score for a single rubric dimension."""

    dimension: str
    score: float
    max_score: float
    feedback: str


class EvaluateResponseResult(BaseModel):
    """Result of evaluating a response."""

    overall_score: float
    max_score: float
    dimensions: list[DimensionScore]
    summary_feedback: str
    growth_tips: list[str]
    star_compliance: Optional[bool] = None
