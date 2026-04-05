from typing import List, Dict, Any, Optional, Tuple
import json
import logging

logger = logging.getLogger(__name__)


class ContextItem:
    def __init__(
        self,
        content: str,
        importance: float = 1.0,
        source: str = "unknown",
        metadata: Optional[Dict] = None,
    ):
        self.content = content
        self.importance = importance
        self.source = source
        self.metadata = metadata or {}
        self._token_count = self._estimate_tokens(content)

    def _estimate_tokens(self, content: str) -> int:
        return len(content) // 4

    @property
    def token_count(self) -> int:
        return self._token_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "importance": self.importance,
            "source": self.source,
            "metadata": self.metadata,
            "token_count": self._token_count,
        }


class ContextManager:
    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens
        self._items: List[ContextItem] = []
        self._importance_weights = {
            "system": 1.0,
            "user": 0.9,
            "recent": 0.8,
            "historical": 0.6,
            "retrieved": 0.5,
        }

    def add(
        self,
        content: str,
        importance: Optional[float] = None,
        source: str = "unknown",
        metadata: Optional[Dict] = None,
    ):
        weight = self._importance_weights.get(source, 0.7)
        final_importance = importance if importance is not None else weight

        item = ContextItem(
            content=content,
            importance=final_importance,
            source=source,
            metadata=metadata,
        )
        self._items.append(item)
        self._optimize()

    def _optimize(self):
        total_tokens = sum(item.token_count for item in self._items)
        if total_tokens <= self.max_tokens:
            return

        sorted_items = sorted(self._items, key=lambda x: x.importance, reverse=True)

        self._items = []
        current_tokens = 0

        for item in sorted_items:
            if current_tokens + item.token_count <= self.max_tokens:
                self._items.append(item)
                current_tokens += item.token_count
            else:
                break

        logger.debug(
            f"Context optimized: {len(sorted_items)} -> {len(self._items)} items"
        )

    def get_context(self) -> str:
        return "\n".join(item.content for item in self._items)

    def get_items(self) -> List[ContextItem]:
        return self._items

    def get_structured_context(self) -> List[Dict[str, Any]]:
        return [item.to_dict() for item in self._items]

    def clear(self):
        self._items = []

    def remove_last(self):
        if self._items:
            self._items.pop()

    def get_total_tokens(self) -> int:
        return sum(item.token_count for item in self._items)


class ContextBuilder:
    def __init__(self):
        self._system_context = ""
        self._items: List[ContextItem] = []

    def with_system(self, content: str):
        self._system_context = content
        return self

    def with_items(self, items: List[ContextItem]):
        self._items.extend(items)
        return self

    def with_user_input(self, content: str):
        self._items.append(
            ContextItem(content=f"用户: {content}", importance=0.9, source="user")
        )
        return self

    def with_memory(self, content: str, importance: float = 0.7):
        self._items.append(
            ContextItem(content=content, importance=importance, source="memory")
        )
        return self

    def with_retrieved(self, content: str, score: float = 0.5):
        self._items.append(
            ContextItem(content=content, importance=score, source="retrieved")
        )
        return self

    def build(self, max_tokens: int = 8000) -> str:
        context_parts = []
        if self._system_context:
            context_parts.append(f"[系统上下文]\n{self._system_context}")

        sorted_items = sorted(self._items, key=lambda x: x.importance, reverse=True)

        current_tokens = len(self._system_context) // 4 if self._system_context else 0
        for item in sorted_items:
            if current_tokens + item.token_count <= max_tokens:
                context_parts.append(f"[{item.source}]\n{item.content}")
                current_tokens += item.token_count

        return "\n\n".join(context_parts)


def merge_duplicate_context(contexts: List[str]) -> str:
    seen = set()
    result = []

    for ctx in contexts:
        if ctx not in seen:
            seen.add(ctx)
            result.append(ctx)

    return "\n\n".join(result)


def compress_context(context: str, max_length: int = 4000) -> str:
    if len(context) <= max_length:
        return context

    sentences = context.split("。")
    result = []
    current_length = 0

    for sentence in sentences:
        sentence_with_punct = sentence + "。"
        if current_length + len(sentence_with_punct) <= max_length * 0.8:
            result.append(sentence_with_punct)
            current_length += len(sentence_with_punct)

    return "".join(result)
