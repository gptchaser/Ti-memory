"""Ti-memory: 片段记忆 · 融会贯通 · 记忆块.

一个受人类记忆片段性启发、面向 LLM 的记忆系统:

- 记忆以"块"为单位独立存储, 用关键词(锚点)作为检索入口;
- 命中关键词后进入块内, 才能看到融合后的整体描述;
- 新记忆若与某块共享关键词, 会被吸收进该块(原片段不再独立存在,
  只作为带衰减强度的溯源记录淡出), 因此记忆块总数增长缓慢;
- 桥接多个块的记忆会把它们合并成更大的块——这就是"融会贯通"。
"""

from .extract import extract_keywords
from .models import MemoryBlock, Source
from .store import JsonStore
from .system import AddResult, MemorySystem

__version__ = "0.3.0"
__all__ = [
    "MemoryBlock",
    "Source",
    "JsonStore",
    "MemorySystem",
    "AddResult",
    "extract_keywords",
    "__version__",
]
