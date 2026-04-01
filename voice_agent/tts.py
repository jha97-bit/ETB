"""Text-to-Speech: Hugging Face Inference API."""

from __future__ import annotations

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


class TextToSpeech:
    """Convert text to speech using Hugging Face Inference API."""

    def __init__(self):
        settings = get_settings()
        self._token = settings.hf_token if settings.hf_token else None
        self._model = settings.hf_tts_model
        self._api_url = f"https://api-inference.huggingface.co/models/{self._model}"

    def synthesize(self, text: str, output_path: Optional[str | Path] = None) -> bytes:
        """Synthesize text to speech. Returns audio bytes or writes to file."""
        if not self._token or not HAS_REQUESTS:
            return b"[TTS unavailable: set HUGGINGFACEHUB_API_TOKEN and install requests]"

        try:
            response = requests.post(
                self._api_url,
                headers={"Authorization": f"Bearer {self._token}"},
                json={"inputs": text},
                timeout=30,
            )
            response.raise_for_status()
            audio_bytes = response.content
            if output_path:
                Path(output_path).write_bytes(audio_bytes)
            return audio_bytes
        except requests.exceptions.HTTPError as e:
            response = getattr(e, "response", None)
            if response and response.status_code == 503:
                return b"[TTS model loading - retry in a few seconds]"
            return f"[HTTP error: {e}]".encode()
        except Exception as e:
            return f"[TTS error: {e}]".encode()
