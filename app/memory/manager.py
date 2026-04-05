from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)


class ShortTermMemory:
    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
        self._conversation_history: List[Dict[str, Any]] = []
        self._current_context: List[Dict[str, Any]] = []

    def add_interaction(
        self, role: str, content: str, metadata: Optional[Dict] = None
    ):
        entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
        self._conversation_history.append(entry)
        self._current_context.append(entry)
        self._trim_context()

    def _trim_context(self):
        total_tokens = sum(len(json.dumps(e)) for e in self._current_context)
        while total_tokens > self.max_tokens and len(self._current_context) > 2:
            removed = self._current_context.pop(0)
            total_tokens -= len(json.dumps(removed))

    def get_recent(self, n: int = 10) -> List[Dict[str, Any]]:
        return self._conversation_history[-n:]

    def get_context(self) -> List[Dict[str, Any]]:
        return self._current_context

    def clear_context(self):
        self._current_context = []

    def search(self, query: str) -> List[Dict[str, Any]]:
        results = []
        for entry in self._conversation_history:
            if query.lower() in entry.get("content", "").lower():
                results.append(entry)
        return results


class LongTermMemory:
    def __init__(self, db_session=None):
        self.db = db_session
        self._memory_cache: Dict[str, Any] = {}

    async def store(
        self,
        memory_type: str,
        content: str,
        metadata: Optional[Dict] = None,
        importance: float = 1.0,
    ) -> int:
        from app.database import Memory, get_db

        db = next(get_db())
        try:
            memory = Memory(
                memory_type=memory_type,
                content=content,
                metadata=metadata or {},
                importance=importance,
            )
            db.add(memory)
            db.commit()
            memory_id = memory.id

            cache_key = f"{memory_type}:{memory_id}"
            self._memory_cache[cache_key] = {
                "id": memory_id,
                "content": content,
                "metadata": metadata,
            }

            return memory_id
        finally:
            db.close()

    async def retrieve(
        self, memory_type: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        from app.database import Memory, get_db

        db = next(get_db())
        try:
            query = db.query(Memory)
            if memory_type:
                query = query.filter(Memory.memory_type == memory_type)
            memories = query.order_by(Memory.importance.desc(), Memory.created_at.desc()).limit(limit).all()

            return [
                {
                    "id": m.id,
                    "type": m.memory_type,
                    "content": m.content,
                    "metadata": m.metadata,
                    "importance": m.importance,
                    "created_at": m.created_at.isoformat(),
                }
                for m in memories
            ]
        finally:
            db.close()

    async def search_by_content(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        from app.database import Memory, get_db

        db = next(get_db())
        try:
            memories = (
                db.query(Memory)
                .filter(Memory.content.contains(query))
                .order_by(Memory.importance.desc())
                .limit(limit)
                .all()
            )

            return [
                {
                    "id": m.id,
                    "type": m.memory_type,
                    "content": m.content,
                    "metadata": m.metadata,
                }
                for m in memories
            ]
        finally:
            db.close()

    async def update_importance(self, memory_id: int, importance: float):
        from app.database import Memory, get_db

        db = next(get_db())
        try:
            memory = db.query(Memory).filter(Memory.id == memory_id).first()
            if memory:
                memory.importance = importance
                db.commit()
        finally:
            db.close()


class MemoryManager:
    def __init__(self, db_session=None):
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory(db_session)

    async def store_interaction(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict] = None,
    ):
        self.short_term.add_interaction(role, content, metadata)

        if metadata and metadata.get("important"):
            await self.long_term.store(
                memory_type="interaction",
                content=content,
                metadata=metadata,
                importance=metadata.get("importance", 1.0),
            )

    async def get_context(self, include_long_term: bool = True) -> str:
        context_parts = []

        recent = self.short_term.get_context()
        for entry in recent:
            context_parts.append(f"{entry['role']}: {entry['content']}")

        if include_long_term:
            relevant_memories = await self.long_term.retrieve(memory_type="interaction", limit=5)
            if relevant_memories:
                context_parts.append("\n--- 长期记忆 ---")
                for mem in relevant_memories:
                    context_parts.append(f"- {mem['content']}")

        return "\n".join(context_parts)

    async def get_relevant_context(self, query: str) -> str:
        recent = self.short_term.search(query)
        long_term = await self.long_term.search_by_content(query)

        context_parts = []
        for entry in recent[-3:]:
            context_parts.append(f"{entry['role']}: {entry['content']}")

        if long_term:
            context_parts.append("\n--- 相关长期记忆 ---")
            for mem in long_term[:3]:
                context_parts.append(f"- {mem['content']}")

        return "\n".join(context_parts) if context_parts else ""

    def clear_short_term(self):
        self.short_term.clear_context()
