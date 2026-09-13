"""Ti-memory 记忆系统门面: 统一入口.

核心流程:
  添加片段 -> 关键词匹配 -> 无匹配则新建块 / 有匹配则吸收进块(可跨块合并)
  -> 关键词检索(概览) -> 进入块内查看整体描述
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from .linking import match_blocks
from .models import MemoryBlock, normalize_keywords
from .retrieval import preview as _preview
from .retrieval import query as _query
from .store import JsonStore
from .synthesis import LLMClient, absorb, create_block, merge_blocks


@dataclass
class AddResult:
    """一次添加的结果."""

    block: MemoryBlock          # 片段最终所在的记忆块
    created: bool               # True=新建了块, False=吸收进已有块
    merged_blocks: list[str]    # 因桥接而被合并掉的旧块 id


class MemorySystem:
    """记忆系统: 独立记忆块 + 关键词检索 + 吸收式融会贯通."""

    def __init__(self, store_path: str = "data/memories.json"):
        self.store = JsonStore(store_path)
        self.llm = LLMClient()
        self._blocks = self.store.load()

    # ---- 写入 ----
    def add(self, content: str, keywords: Iterable[str]) -> AddResult:
        """添加一条记忆片段.

        与某块共享关键词 -> 被吸收进该块(原片段淡出, 只留溯源);
        与多个块共享关键词 -> 桥接合并这些块; 否则新建一个块。
        """
        kws = normalize_keywords(keywords)
        matched = match_blocks(self._blocks, kws)

        if not matched:
            block = create_block(content, kws, self.llm)
            self._blocks.append(block)
            self._save()
            return AddResult(block=block, created=True, merged_blocks=[])

        if len(matched) == 1:
            block = matched[0]
            absorb(block, content, kws, self.llm)
            self._save()
            return AddResult(block=block, created=False, merged_blocks=[])

        # 新片段桥接多个块: 合并成一个大块
        old_ids = [b.id for b in matched]
        merged = merge_blocks(matched, self.llm)
        absorb(merged, content, kws, self.llm)
        self._blocks = [b for b in self._blocks if b.id not in old_ids]
        self._blocks.append(merged)
        self._save()
        return AddResult(block=merged, created=False, merged_blocks=old_ids)

    # ---- 读取 ----
    @property
    def blocks(self) -> list[MemoryBlock]:
        return list(self._blocks)

    def get(self, block_id: str) -> Optional[MemoryBlock]:
        """进入记忆块, 查看整体描述与衰减中的溯源片段."""
        for b in self._blocks:
            if b.id == block_id:
                return b
        return None

    # ---- 检索 ----
    def query(self, tokens: Iterable[str], limit: int = 10) -> list[dict]:
        """关键词检索: 返回块概览(关键词 + 开头预览); 整体描述需 get 进入."""
        return [_preview(b) for b in _query(self._blocks, tokens, limit)]

    # ---- 持久化 ----
    def _save(self) -> None:
        self.store.save(self._blocks)
