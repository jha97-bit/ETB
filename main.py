"""Mock Interview AI – Main FastAPI application."""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from shared.schemas import (
    InterviewMode,
    AskQuestionRequest,
    AskQuestionResponse,
    QAPair,
    MemoryEvent,
    RecallContextRequest,
    RecallContextResponse,
    EvaluateResponseRequest,
    EvaluateResponseResult,
)
from orchestrator.agent import OrchestratorAgent
from memory.service import MemoryService
from evaluation.engine import EvaluationEngine
from guardrails.filters import GuardrailsFilter
from voice_agent import VoiceOrchestrator, SpeechToText, TextToSpeech
from shared.config import get_settings

# Optional LangSmith tracing: enabled only when env vars are set.
get_settings().configure_langsmith()

# Initialize services
orchestrator = OrchestratorAgent()
memory = MemoryService()
evaluator = EvaluationEngine()
guardrails = GuardrailsFilter()

def _ask_question(req: AskQuestionRequest) -> AskQuestionResponse:
    return orchestrator.ask_question(req)

voice_orchestrator = VoiceOrchestrator(ask_question_fn=_ask_question)

app = FastAPI(
    title="Mock Interview AI",
    description="Adaptive mock interview platform with memory, evaluation, guardrails, and voice.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# HITL events file
EVENTS_FILE = Path(__file__).parent / "data" / "hitl_events.json"


# --- Orchestrator (A) ---
@app.post("/ask_question", response_model=AskQuestionResponse)
def ask_question(request: AskQuestionRequest) -> AskQuestionResponse:
    """Get the next interview question (text mode)."""
    # Guardrail: check if last answer was safe
    if request.last_answer:
        fr = guardrails.check_response(request.last_answer)
        if not fr.passed:
            _append_hitl_event({"session_id": request.session_id, "reason": fr.reason, "type": "response_blocked"})
            raise HTTPException(status_code=400, detail=fr.reason or "Response blocked by guardrails")

    response = orchestrator.ask_question(request)
    # Guardrail: check question is appropriate
    qr = guardrails.check_question(response.question)
    if not qr.passed:
        _append_hitl_event({"session_id": request.session_id, "reason": qr.reason, "question": response.question})
        raise HTTPException(status_code=400, detail=qr.reason or "Question blocked by guardrails")
    return response


# --- Memory (B) ---
@app.post("/memory/save")
def save_event(event: MemoryEvent) -> dict:
    """Save an event to memory."""
    event_id = memory.save_event(event)
    return {"event_id": event_id}


@app.post("/memory/recall", response_model=RecallContextResponse)
def recall_context(request: RecallContextRequest) -> RecallContextResponse:
    """Recall context for a session."""
    return memory.recall_context(request)


# --- Evaluation (C) ---
@app.post("/evaluate", response_model=EvaluateResponseResult)
def evaluate_response(request: EvaluateResponseRequest) -> EvaluateResponseResult:
    """Evaluate a candidate response and return scorecard + feedback."""
    result = evaluator.evaluate_response(request)
    # Guardrail: check feedback is constructive
    fr = guardrails.check_feedback(result.summary_feedback)
    if fr.flagged:
        _append_hitl_event({"type": "feedback_flagged", "summary": result.summary_feedback})
    return result


# --- Voice (Extension) ---
@app.post("/voice/ask")
async def voice_ask(
    session_id: str = Form(...),
    user_id: str = Form(...),
    mode: str = Form("behavioral"),
    last_question: str = Form(None),
    audio: UploadFile = File(...),
) -> dict:
    """Process user speech, return next question as text and audio."""
    audio_bytes = await audio.read()
    stt = SpeechToText()
    transcript = stt.transcribe_bytes(audio_bytes, audio.filename or "audio.webm")

    conv_history = []  # Could be fetched from memory
    interview_mode = InterviewMode(mode) if mode in [m.value for m in InterviewMode] else InterviewMode.BEHAVIORAL

    question, audio_out = voice_orchestrator.process_user_speech(
        audio_bytes=audio_bytes,
        session_id=session_id,
        user_id=user_id,
        mode=interview_mode,
        last_question=last_question or None,
        conversation_history=conv_history,
    )
    # Return JSON with base64 audio for simplicity
    import base64
    return {
        "question": question,
        "audio_base64": base64.b64encode(audio_out).decode() if isinstance(audio_out, bytes) else None,
    }


@app.post("/voice/start")
def voice_start(
    session_id: str = Form(...),
    user_id: str = Form(...),
    mode: str = Form("behavioral"),
) -> dict:
    """Get the first question as text and audio (for voice mode)."""
    interview_mode = InterviewMode(mode) if mode in [m.value for m in InterviewMode] else InterviewMode.BEHAVIORAL
    question, audio_out = voice_orchestrator.get_initial_question_audio(session_id, user_id, interview_mode)
    import base64
    return {
        "question": question,
        "audio_base64": base64.b64encode(audio_out).decode() if isinstance(audio_out, bytes) else None,
    }


# --- TTS / STT helpers (for clients) ---
@app.post("/tts")
async def tts_synthesize(text: str) -> bytes:
    """Synthesize text to speech. Returns audio bytes."""
    tts = TextToSpeech()
    return tts.synthesize(text)


def _append_hitl_event(evt: dict) -> None:
    EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    events = json.loads(EVENTS_FILE.read_text()) if EVENTS_FILE.exists() else []
    events.append(evt)
    EVENTS_FILE.write_text(json.dumps(events, indent=2))


@app.get("/")
def root():
    return {"message": "Mock Interview AI", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
