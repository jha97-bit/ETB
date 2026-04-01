"""Speech-to-Text: Hugging Face Whisper Inference API."""

from __future__ import annotations

import base64
import tempfile
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.config import get_settings

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class SpeechToText:
    """Convert speech to text using Hugging Face Inference API (Whisper)."""

    def __init__(self):
        settings = get_settings()
        self._token = settings.hf_token if settings.hf_token else None
        self._model = settings.hf_whisper_model
        self._api_url = f"https://api-inference.huggingface.co/models/{self._model}"

    def transcribe(self, audio_path: str | Path) -> str:
        """Transcribe audio file to text."""
        if not self._token or not HAS_REQUESTS:
            return "[STT unavailable: set HUGGINGFACEHUB_API_TOKEN and install requests]"

        try:
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            return self._transcribe_bytes(audio_bytes)
        except Exception as e:
            return f"[Transcription error: {e}]"

    def transcribe_bytes(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        """Transcribe audio bytes to text."""
        if not self._token or not HAS_REQUESTS:
            return "[STT unavailable: set HUGGINGFACEHUB_API_TOKEN and install requests]"
        return self._transcribe_bytes(audio_bytes)

    def _transcribe_bytes(self, audio_bytes: bytes) -> str:
        try:
            response = requests.post(
                self._api_url,
                headers={"Authorization": f"Bearer {self._token}"},
                data=audio_bytes,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and "text" in data:
                return data["text"].strip()
            if isinstance(data, dict) and "transcription" in data:
                return data["transcription"].strip()
            if isinstance(data, str):
                return data.strip()
            return str(data)
        except requests.exceptions.HTTPError as e:
            if response.status_code == 503:
                return "[Model loading - retry in a few seconds]"
            return f"[HTTP error: {e}]"
        except Exception as e:
            return f"[Transcription error: {e}]"
