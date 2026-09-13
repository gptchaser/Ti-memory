"""核心数据模型: 记忆块(MemoryBlock) 与被吸收的片段(Source).

设计(来自灵感): 人的记忆是片段化的——我们记住的是一条条独立的通路
(A→B、C→B), 而不是一张完整的图。记忆以"块"为单位:

- 每个记忆块独立存储, 用关键词(锚点, 如 A、B、C)作为检索入口;
- 关键词命中块后, "进入"块内才能看到整体描述;
- 新记忆若与某块共享关键词, 会被**吸收**进该块(原片段不再独立存在,
  只作为带衰减强度的溯源记录, 逐渐淡出);
- 因此记忆块的总数增长缓慢, 不会随片段数量线性膨胀。
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def normalize_keywords(keywords: Any) -> list[str]:
    """清洗关键词: 去空白、去重、保持顺序."""
    seen: set[str] = set()
    out: list[str] = []
    for k in keywords or []:
        k = str(k).strip()
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


@dataclass
class Source:
    """一条被吸收进记忆块的原始片段(已淡出独立检索).

    strength 随时间衰减: 每经过一个半衰期强度减半。
    """

    content: str
    keywords: list[str] = field(default_factory=list)
    absorbed_at: float = field(default_factory=time.time)
    strength: float = 1.0
    id: str = field(default_factory=_new_id)

    def effective_strength(self, half_life_days: float = 30.0) -> float:
        """当前有效强度(考虑时间衰减)."""
        age_days = max(0.0, (time.time() - self.absorbed_at) / 86400.0)
        return self.strength * (0.5 ** (age_days / half_life_days))


@dataclass
class MemoryBlock:
    """一个独立记忆块: 关键词(检索入口) + 整体描述(进入后查看).

    - keywords: 检索关键词(锚点), 顺序尽量保持通路先后;
    - content:  融合后的整体描述, 由 sources 渲染而成;
    - sources:  被吸收进本块的片段溯源(随时间衰减);
    - links:    关键词邻接对, 用于识别"A→B→C"式通路。
    """

    content: str
    keywords: list[str] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    links: list[list[str]] = field(default_factory=list)
    strength: float = 1.0
    id: str = field(default_factory=_new_id)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "keywords": self.keywords,
            "sources": [s.__dict__.copy() for s in self.sources],
            "links": [list(p) for p in self.links],
            "strength": self.strength,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryBlock":
        return cls(
            id=data.get("id") or _new_id(),
            content=data.get("content", ""),
            keywords=list(data.get("keywords", [])),
            sources=[
                Source(**{k: v for k, v in s.items() if k in Source.__dataclass_fields__})
                for s in data.get("sources", [])
            ],
            links=[list(p) for p in data.get("links", [])],
            strength=data.get("strength", 1.0),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )

    @property
    def chain(self) -> Optional[list[str]]:
        """由 links 识别的通路(如 [A, B, C]); 不是通路则返回 None.

        融会贯通需要至少两条片段参与, 单条片段的自身顺序不算通路。
        """
        from .linking import chain_path

        if len(self.sources) < 2:
            return None
        return chain_path(self.keywords, self.links)

    def effective_strength(self, half_life_days: float = 30.0) -> float:
        """当前有效强度(考虑时间衰减): 每经过一个半衰期减半.

        记忆遗忘模型: 长时间不被检索的块会逐渐变弱,
        检索/进入会加强(use it or lose it)。
        """
        age_days = max(0.0, (time.time() - self.updated_at) / 86400.0)
        return self.strength * (0.5 ** (age_days / half_life_days))
