"""关联发现: 关键词匹配与通路识别.

- match_blocks: 找出与给定关键词共享至少一个关键词的记忆块;
- chain_path:   若关键词图恰好构成一条通路(连通且最大度 <= 2),
                返回有序路径 A→B→C, 否则返回 None。
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Optional

from .models import MemoryBlock


def match_blocks(blocks: Iterable[MemoryBlock], keywords: Iterable[str]) -> list[MemoryBlock]:
    """返回与关键词共享至少一个关键词的记忆块."""
    kw = set(keywords)
    return [b for b in blocks if kw & set(b.keywords)]


def chain_path(
    keywords: Iterable[str], edges: Iterable[tuple[str, str]]
) -> Optional[list[str]]:
    """若锚点图恰好是一条通路(连通且最大度 <= 2), 返回有序路径; 否则返回 None.

    例如关键词 {A, B, C}、边 {A-B, C-B} 得到 ["A", "B", "C"]。
    """
    nodes = sorted(set(keywords))
    adj: dict[str, set[str]] = defaultdict(set)
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)

    if any(len(adj[n]) > 2 for n in nodes):
        return None  # 存在分支, 是网络而非通路

    if len(nodes) == 1:
        return nodes

    starts = [n for n in nodes if len(adj[n]) == 1]
    if len(starts) != 2:
        return None  # 有环或存在孤立关键词

    path: list[str] = []
    current, prev = starts[0], None
    while True:
        path.append(current)
        nxts = [n for n in adj[current] if n != prev]
        if not nxts:
            break
        current, prev = nxts[0], current

    return path if len(path) == len(nodes) else None
