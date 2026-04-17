"""Configuration and environment loading."""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

# Load .env from project root (parent of 'shared') so it works regardless of cwd
_project_root = Path(__file__).resolve().parent.parent
load_dotenv(_project_root / ".env")
load_dotenv()  # also allow override from current directory


@lru_cache
def get_settings() -> "Settings":
    return Settings()


class Settings(BaseModel):
    """Application settings from environment."""

    # Hugging Face (primary)
    hf_token: str = os.getenv("HUGGINGFACEHUB_API_TOKEN", "") or os.getenv("HF_TOKEN", "")
    chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")

    # Model IDs
    hf_llm_model: str = os.getenv("HF_LLM_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
    hf_embedding_model: str = os.getenv("HF_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    hf_whisper_model: str = os.getenv("HF_WHISPER_MODEL", "openai/whisper-large-v3")
    hf_tts_model: str = os.getenv("HF_TTS_MODEL", "facebook/mms-tts-eng")
    hf_skip_embeddings: bool = os.getenv("HF_SKIP_EMBEDDINGS", "false").lower() == "true"

    # Legacy OpenAI (optional fallback)
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

    # Guardrails
    rebuff_api_key: str = os.getenv("REBUFF_API_KEY", "")

    # LangSmith tracing (optional)
    langsmith_api_key: str = os.getenv("LANGSMITH_API_KEY", "")
    langsmith_project: str = os.getenv("LANGSMITH_PROJECT", "etb-mock-interview")
    langsmith_tracing_v2: bool = os.getenv("LANGSMITH_TRACING_V2", "false").lower() == "true"
    langsmith_endpoint: str = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")

    @property
    def has_hf(self) -> bool:
        return bool(self.hf_token)

    @property
    def has_voice(self) -> bool:
        return bool(self.hf_token)

    @property
    def has_langsmith(self) -> bool:
        return bool(self.langsmith_api_key) and self.langsmith_tracing_v2

    def configure_langsmith(self) -> None:
        """Set LangSmith runtime env vars for LangChain tracing."""
        if not self.has_langsmith:
            return
        os.environ["LANGSMITH_API_KEY"] = self.langsmith_api_key
        os.environ["LANGSMITH_PROJECT"] = self.langsmith_project
        os.environ["LANGSMITH_TRACING_V2"] = "true"
        os.environ["LANGSMITH_ENDPOINT"] = self.langsmith_endpoint
