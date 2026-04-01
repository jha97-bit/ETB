"""Memory Manager: short-term, episodic, and long-term memory with vector store."""

from datetime import datetime
from typing import Optional

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.schemas import MemoryEvent, RecallContextRequest, RecallContextResponse
from shared.config import get_settings

# Hugging Face embeddings
try:
    from langchain_huggingface import HuggingFaceEmbeddings
    HAS_HF_EMBEDDINGS = True
except ImportError:
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        HAS_HF_EMBEDDINGS = True
    except ImportError:
        HAS_HF_EMBEDDINGS = False


class MemoryManager:
    """Manages short-term (session), episodic (transcript), and long-term (personalization) memory."""

    def __init__(self):
        settings = get_settings()
        self._settings = settings
        self._embeddings = None
        self._vector_store = None
        self._embeddings_tried = False

        persist_dir = Path(settings.chroma_persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)
        self._persist_dir = str(persist_dir)

        # In-memory short-term store (always used)
        self._session_store: dict[str, list[MemoryEvent]] = {}
        self._weak_skills: dict[str, list[str]] = {}

    def _get_embeddings(self):
        """Lazy-load embeddings to avoid blocking app startup (e.g. offline)."""
        if self._embeddings_tried:
            return self._embeddings
        self._embeddings_tried = True
        if self._settings.hf_skip_embeddings:
            return None
        if self._settings.hf_token and HAS_HF_EMBEDDINGS:
            try:
                try:
                    self._embeddings = HuggingFaceEmbeddings(
                        model=self._settings.hf_embedding_model,
                        model_kwargs={"device": "cpu"},
                        encode_kwargs={"normalize_embeddings": True},
                    )
                except TypeError:
                    self._embeddings = HuggingFaceEmbeddings(
                        model_name=self._settings.hf_embedding_model,
                        model_kwargs={"device": "cpu"},
                        encode_kwargs={"normalize_embeddings": True},
                    )
                self._vector_store = Chroma(
                    collection_name="interview_memory",
                    embedding_function=self._embeddings,
                    persist_directory=self._persist_dir,
                )
            except Exception:
                pass
        return self._embeddings

    def save_event(self, event: MemoryEvent) -> str:
        """Save an event to memory. Returns event ID."""
        session_key = f"{event.user_id}:{event.session_id}"
        if session_key not in self._session_store:
            self._session_store[session_key] = []
        self._session_store[session_key].append(event)

        if self._get_embeddings() and self._vector_store and event.content:
            text = _event_to_text(event)
            doc = Document(page_content=text, metadata={
                "session_id": event.session_id,
                "user_id": event.user_id,
                "event_type": event.event_type,
                "timestamp": datetime.utcnow().isoformat(),
            })
            self._vector_store.add_documents([doc])

        return f"{session_key}:{len(self._session_store[session_key]) - 1}"

    def recall_context(self, request: RecallContextRequest) -> RecallContextResponse:
        """Recall relevant context for a session/user."""
        session_key = f"{request.user_id}:{request.session_id}"
        events: list[MemoryEvent] = []

        if session_key in self._session_store:
            recent = self._session_store[session_key][-request.limit:]
            if request.event_types:
                recent = [e for e in recent if e.event_type in request.event_types]
            events.extend(recent)

        if self._get_embeddings() and self._vector_store and request.query:
            try:
                docs = self._vector_store.similarity_search(request.query, k=request.limit)
                for doc in docs:
                    if doc.metadata.get("user_id") == request.user_id and doc.metadata.get("session_id") == request.session_id:
                        events.append(_doc_to_event(doc, request.user_id, request.session_id))
            except Exception:
                pass

        weak_skills = self._weak_skills.get(request.user_id, [])
        return RecallContextResponse(
            events=events[:request.limit * 2],
            weak_skills=weak_skills if weak_skills else None,
        )

    def track_weak_skill(self, user_id: str, skill: str) -> None:
        """Record a weak skill for personalization."""
        if user_id not in self._weak_skills:
            self._weak_skills[user_id] = []
        if skill not in self._weak_skills[user_id]:
            self._weak_skills[user_id].append(skill)


def _event_to_text(event: MemoryEvent) -> str:
    parts = [f"[{event.event_type}]"]
    for k, v in event.content.items():
        parts.append(f"{k}: {v}")
    return " ".join(str(p) for p in parts)


def _doc_to_event(doc: Document, user_id: str, session_id: str) -> MemoryEvent:
    return MemoryEvent(
        session_id=session_id,
        user_id=user_id,
        event_type=doc.metadata.get("event_type", "unknown"),
        content={"content": doc.page_content},
        metadata=doc.metadata,
    )


class _DummyEmbeddings:
    """Dummy embeddings when HF token is not set (384 dims for sentence-transformers)."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 384 for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.0] * 384
