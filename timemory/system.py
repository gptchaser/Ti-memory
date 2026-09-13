"""Ti-memory 记忆系统门面: 统一入口.

核心流程:
  添加片段(可自动提取关键词) -> 关键词匹配
    - 无匹配: 新建记忆块
    - 单块匹配: 吸收进该块
    - 片段关键词被某块完全覆盖: 只吸收进最强块(不合并, 防止块膨胀)
    - 片段桥接多块: 合并成一个大块(融会贯通)
  -> 关键词检索(概览 + 关联块) -> 进入块内查看整体描述
  -> 记忆遗忘: 块强度随时间衰减, 检索/进入会加强; 弱块可归档清理
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable, Optional

from .extract import extract_keywords
from .linking import match_blocks
from .models import MemoryBlock, normalize_keywords
from .retrieval import preview as _preview
from .retrieval import query as _query
from .store import JsonStore
from .synthesis import LLMClient, absorb, create_block, merge_blocks

REINFORCE_STEP = 0.25   # 每次检索/进入对块的加强幅度
DEFAULT_PRUNE_THRESHOLD = 0.2
DEFAULT_ARCHIVE_PATH = "data/archive.json"


@dataclass
class AddResult:
    """一次添加的结果."""

    block: MemoryBlock          # 片段最终所在的记忆块
    created: bool               # True=新建了块, False=吸收进已有块
    merged_blocks: list[str]    # 因桥接而被合并掉的旧块 id


class MemorySystem:
    """记忆系统: 独立记忆块 + 关键词检索 + 吸收式融会贯通 + 遗忘."""

    def __init__(self, store_path: str = "data/memories.json"):
        self.store = JsonStore(store_path)
        self.llm = LLMClient()
        self._blocks = self.store.load()

    # ---- 写入 ----
    def add(self, content: str, keywords: Optional[Iterable[str]] = None) -> AddResult:
        """添加一条记忆片段.

        不传 keywords 时自动提取(LLM 或规则兜底)。
        与某块共享关键词 -> 被吸收进该块(原片段淡出, 只留溯源);
        关键词被某块完全覆盖 -> 只吸收进最强块;
        片段桥接多个块 -> 合并这些块(融会贯通); 否则新建一个块。
        """
        kws = normalize_keywords(keywords) if keywords is not None else extract_keywords(
            content, self.llm
        )
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

        # 片段关键词被某个块完全覆盖 -> 吸收进最强块, 不合并(防止膨胀)
        if any(set(kws) <= set(b.keywords) for b in matched):
            block = self._best_block(matched, kws)
            absorb(block, content, kws, self.llm)
            self._save()
            return AddResult(block=block, created=False, merged_blocks=[])

        # 片段桥接多个块: 合并成一个大块
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
        """进入记忆块, 查看整体描述与溯源片段; 同时加强该块(用进废退)."""
        for b in self._blocks:
            if b.id == block_id:
                self._reinforce(b)
                self._save()
                return b
        return None

    # ---- 检索 ----
    def query(self, tokens: Iterable[str], limit: int = 10) -> list[dict]:
        """关键词检索: 返回块概览, 并附上与命中块共享关键词的关联块.

        检索会加强命中块; 整体描述需 get 进入查看。
        """
        hits = _query(self._blocks, tokens, limit)
        for b in hits:
            self._reinforce(b)
        if hits:
            self._save()
        out = []
        for b in hits:
            info = _preview(b)
            info["related"] = [
                _preview(r)
                for r in self._blocks
                if r.id != b.id and (set(r.keywords) & set(b.keywords))
            ][:3]
            out.append(info)
        return out

    # ---- 遗忘 ----
    def prune(
        self,
        threshold: float = DEFAULT_PRUNE_THRESHOLD,
        archive_path: str = DEFAULT_ARCHIVE_PATH,
    ) -> list[MemoryBlock]:
        """把强度低于阈值的弱块归档(移出活跃记忆, 不删除)."""
        weak = [b for b in self._blocks if b.effective_strength() < threshold]
        if weak:
            archive = JsonStore(archive_path)
            archived = archive.load()
            archived.extend(weak)
            archive.save(archived)
            weak_ids = {b.id for b in weak}
            self._blocks = [b for b in self._blocks if b.id not in weak_ids]
            self._save()
        return weak

    # ---- 统计 ----
    def stats(self) -> dict:
        """记忆健康统计: 块数 vs 片段总数(直观展示"总数不膨胀")."""
        total_sources = sum(len(b.sources) for b in self._blocks)
        n = len(self._blocks)
        return {
            "blocks": n,
            "fragments": total_sources,
            "avg_sources_per_block": round(total_sources / n, 2) if n else 0.0,
            "total_keywords": sum(len(b.keywords) for b in self._blocks),
            "chains": sum(
                1 for b in self._blocks if b.chain and len(b.chain) >= 3
            ),
        }

    # ---- 内部 ----
    def _best_block(self, matched: list[MemoryBlock], kws: list[str]) -> MemoryBlock:
        """在多个命中块中选最强: 共享关键词数 > 有效强度 > 最近更新."""

        def key(b: MemoryBlock) -> tuple:
            shared = len(set(b.keywords) & set(kws))
            return (shared, b.effective_strength(), b.updated_at)

        return max(matched, key=key)

    def _reinforce(self, block: MemoryBlock) -> None:
        """检索/进入时加强记忆(用进废退)."""
        block.strength = min(1.0, block.strength + REINFORCE_STEP)
        block.updated_at = time.time()

    def _save(self) -> None:
        self.store.save(self._blocks)
