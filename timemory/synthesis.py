"""融会贯通: 片段吸收与整体描述生成.

新记忆共享某块的关键词时, 被**吸收**进该块: 关键词并集、链接更新、
整体描述重新渲染; 原片段不再独立存在, 只作为带衰减强度的溯源记录。

默认使用规则版渲染(确定性、可测试); 配置 LLM 环境变量后,
可由大模型生成更自然连贯的整体描述。
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Iterable, Optional

from .linking import chain_path
from .models import MemoryBlock, Source

DEFAULT_LLM_BASE_URL = "https://api.openai.com/v1"
DEFAULT_LLM_MODEL = "gpt-4o-mini"


class LLMClient:
    """可选的大模型后端(OpenAI 兼容接口).

    环境变量:
      TI_MEMORY_LLM_BASE_URL  接口地址, 默认 https://api.openai.com/v1
      TI_MEMORY_LLM_API_KEY   密钥(未配置则走规则版兜底)
      TI_MEMORY_LLM_MODEL     模型名, 默认 gpt-4o-mini
    """

    def __init__(self) -> None:
        self.base_url = os.environ.get("TI_MEMORY_LLM_BASE_URL", DEFAULT_LLM_BASE_URL).rstrip("/")
        self.api_key = os.environ.get("TI_MEMORY_LLM_API_KEY", "")
        self.model = os.environ.get("TI_MEMORY_LLM_MODEL", DEFAULT_LLM_MODEL)

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def chat(self, messages: list[dict]) -> Optional[str]:
        if not self.available:
            return None
        payload = json.dumps({"model": self.model, "messages": messages}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        except (urllib.error.URLError, KeyError, IndexError, OSError):
            return None

    def render(self, sources: Iterable[Source], chain: Optional[list[str]]) -> Optional[str]:
        """让 LLM 把块内片段写成一段完整连贯的整体描述."""
        items = list(sources)
        lines = "\n".join(f"- [{s.id}] {s.content}" for s in items)
        chain_text = " -> ".join(chain) if chain else "、".join(
            sorted({k for s in items for k in s.keywords})
        )
        prompt = (
            "你是一个记忆整合引擎。以下是一个记忆块内被吸收的若干片段, "
            "它们因共享关键词而彼此关联。\n"
            f"片段:\n{lines}\n"
            f"关键词 / 通路: {chain_text}\n"
            "请把它们融会贯通成一段完整、连贯、不重复的整体记忆(中文, 不超过200字), "
            "保留所有关键事实与关联关系。"
        )
        return self.chat([{"role": "user", "content": prompt}])


def rule_based_render(sources: Iterable[Source], chain: Optional[list[str]]) -> str:
    """规则版渲染: 按片段编号列出事实, 末尾标注融会贯通的通路."""
    items = list(sources)
    parts = [f"[{i}] {s.content}" for i, s in enumerate(items, 1)]
    if chain and len(chain) >= 3:
        parts.append(f"融会贯通: {' → '.join(chain)}")
    return "\n".join(parts)


def render_description(
    sources: Iterable[Source], chain: Optional[list[str]], llm: Optional[LLMClient] = None
) -> str:
    """渲染整体描述: 优先 LLM, 失败或未配置则用规则版."""
    if llm is not None and llm.available:
        content = llm.render(sources, chain)
        if content:
            return content
    return rule_based_render(sources, chain)


def update_block_links(block: MemoryBlock, keywords: Iterable[str]) -> None:
    """把一段新片段的相邻关键词对加入块的链接表."""
    kws = list(keywords)
    for a, b in zip(kws, kws[1:]):
        pair = sorted((a, b))
        if pair not in block.links:
            block.links.append(pair)


def absorb(block: MemoryBlock, content: str, keywords: Iterable[str], llm: Optional[LLMClient] = None) -> None:
    """把一条新片段吸收进记忆块: 关键词并集、链接更新、描述重渲染.

    原片段不再独立存在, 以 Source 形式记录(强度随时间衰减)。
    """
    kws = list(keywords)
    for k in kws:
        if k not in block.keywords:
            block.keywords.append(k)
    update_block_links(block, kws)
    block.sources.append(Source(content=content, keywords=kws))
    block.content = render_description(block.sources, block.chain, llm)
    block.updated_at = time.time()


def create_block(content: str, keywords: Iterable[str], llm: Optional[LLMClient] = None) -> MemoryBlock:
    """用第一条片段创建一个记忆块."""
    kws = list(keywords)
    block = MemoryBlock(content="", keywords=kws)
    update_block_links(block, kws)
    block.sources.append(Source(content=content, keywords=kws))
    block.content = render_description(block.sources, block.chain, llm)
    return block


def merge_blocks(blocks: Iterable[MemoryBlock], llm: Optional[LLMClient] = None) -> MemoryBlock:
    """合并多个共享关键词的记忆块为一个新块(新片段桥接场景).

    关键词按出现顺序并集, 链接取并集, 溯源片段全部保留。
    """
    items = list(blocks)
    merged = MemoryBlock(content="")
    seen: set[str] = set()
    for b in items:
        for k in b.keywords:
            if k not in seen:
                seen.add(k)
                merged.keywords.append(k)
        for pair in b.links:
            if pair not in merged.links:
                merged.links.append(list(pair))
        for s in b.sources:
            merged.sources.append(s)
    merged.content = render_description(merged.sources, merged.chain, llm)
    merged.updated_at = time.time()
    return merged
