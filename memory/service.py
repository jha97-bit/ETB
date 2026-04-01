"""Memory service API layer."""

from .manager import MemoryManager
from shared.schemas import MemoryEvent, RecallContextRequest, RecallContextResponse


class MemoryService:
    """Service facade for memory operations."""

    def __init__(self):
        self._manager = MemoryManager()

    def save_event(self, event: MemoryEvent) -> str:
        return self._manager.save_event(event)

    def recall_context(self, request: RecallContextRequest) -> RecallContextResponse:
        return self._manager.recall_context(request)

    def track_weak_skill(self, user_id: str, skill: str) -> None:
        self._manager.track_weak_skill(user_id, skill)
