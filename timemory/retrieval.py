"""关键词检索: 命中记忆块, 返回概览(进入块内才能看到整体描述)."""

from __future__ import annotations

from typing import Iterable

from .models import MemoryBlock


def _preview(content: str, limit: int = 60) -> str:
    first_line = content.split("\n", 1)[0]
    return first_line if len(first_line) <= limit else first_line[:limit] + "…"


def query(blocks: Iterable[MemoryBlock], tokens: Iterable[str], limit: int = 10) -> list[MemoryBlock]:
    """按关键词(或内容关键词)检索记忆块.

    - 关键词命中权重高于内容命中
    - 命中块即返回, 整体描述需通过 get(block_id) 进入查看
    """
    items = list(blocks)
    token_set = {t.strip() for t in tokens if t.strip()}

    def score(b: MemoryBlock) -> int:
        s = 0
        for t in token_set:
            if t in b.keywords:
                s += 2
            if t in b.content:
                s += 1
        return s

    scored = [(score(b), b) for b in items]
    matched = [b for s, b in scored if s > 0]
    matched.sort(key=lambda item: (score(item), item.updated_at), reverse=True)
    return matched[:limit]


def preview(b: MemoryBlock) -> dict:
    """块的外层概览: 只露关键词与开头, 完整描述要进入块内."""
    return {
        "id": b.id,
        "keywords": b.keywords,
        "preview": _preview(b.content),
        "n_sources": len(b.sources),
        "updated_at": b.updated_at,
    }
