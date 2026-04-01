"""Voice orchestrator: STT → Orchestrator → TTS for spoken interviews."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.schemas import AskQuestionRequest, AskQuestionResponse, InterviewMode
from .stt import SpeechToText
from .tts import TextToSpeech


class VoiceOrchestrator:
    """Orchestrates voice-based mock interviews: speech in → question audio out."""

    def __init__(self, ask_question_fn: Callable[[AskQuestionRequest], AskQuestionResponse]):
        self._stt = SpeechToText()
        self._tts = TextToSpeech()
        self._ask_question = ask_question_fn

    def process_user_speech(
        self,
        audio_path: Optional[str | Path] = None,
        audio_bytes: Optional[bytes] = None,
        session_id: str = "",
        user_id: str = "",
        mode: InterviewMode = InterviewMode.BEHAVIORAL,
        last_question: Optional[str] = None,
        conversation_history: Optional[list] = None,
    ) -> tuple[str, bytes]:
        """
        Process user speech: transcribe → get next question → synthesize to audio.
        Provide either audio_path or audio_bytes.
        Returns (question_text, audio_bytes).
        """
        if audio_bytes is not None:
            transcript = self._stt.transcribe_bytes(audio_bytes, "audio.webm")
        elif audio_path:
            transcript = self._stt.transcribe(audio_path)
        else:
            transcript = ""

        request = AskQuestionRequest(
            session_id=session_id,
            user_id=user_id,
            mode=mode,
            last_answer=transcript if transcript else None,
            last_question=last_question,
            conversation_history=conversation_history,
        )
        response = self._ask_question(request)

        audio_bytes = self._tts.synthesize(response.question)
        return response.question, audio_bytes

    def get_initial_question_audio(
        self,
        session_id: str,
        user_id: str,
        mode: InterviewMode = InterviewMode.BEHAVIORAL,
    ) -> tuple[str, bytes]:
        """Get the first question as text and audio."""
        request = AskQuestionRequest(session_id=session_id, user_id=user_id, mode=mode)
        response = self._ask_question(request)
        audio_bytes = self._tts.synthesize(response.question)
        return response.question, audio_bytes
