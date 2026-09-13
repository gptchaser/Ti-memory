"""关键词(锚点)自动提取.

规则版兜底: 中文取连续汉字片段(2-6字), 英文取词, 按 频率×长度 打分并过滤停用词;
配置 LLM 后由大模型直接抽取更准确的关键词。
"""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Optional

from .synthesis import LLMClient

_CJK_RUN = re.compile(r"[\u4e00-\u9fff]{2,6}")
_EN_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]{2,}")

_CJK_STOP = {
    "一个", "可以", "就是", "这个", "那个", "然后", "自己", "我们", "你们", "他们",
    "什么", "这样", "那样", "时候", "地方", "每天", "大概", "一直", "到了", "开始",
    "因为", "所以", "但是", "如果", "还有", "已经", "现在", "今天", "明天", "这里", "那里",
}
_EN_STOP = {
    "the", "and", "for", "are", "but", "not", "you", "all", "any", "can", "her",
    "was", "one", "our", "out", "day", "get", "has", "him", "his", "how", "man",
    "new", "now", "old", "see", "two", "way", "who", "boy", "did", "its", "let",
    "put", "say", "she", "too", "use", "that", "with", "have", "this", "will",
    "your", "from", "into", "them", "then", "they", "were", "when", "what", "about",
    "every", "some", "more", "than", "been", "just", "also", "over", "would", "could",
}


def _parse_keyword_list(text: str) -> list[str]:
    """从 LLM 回复中解析关键词 JSON 数组(带逗号/换行兜底)."""
    if not text:
        return []
    m = re.search(r"\[.*?\]", text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(0))
            if isinstance(data, list):
                return [str(x).strip() for x in data if str(x).strip()]
        except json.JSONDecodeError:
            pass
    return [x.strip().strip('"\'') for x in re.split(r"[,，\n]", text) if x.strip()]


def _rule_extract(content: str, top_n: int) -> list[str]:
    """规则提取: 连续汉字片段 + 英文单词, 按 频率×长度 排序."""
    scores: Counter[str] = Counter()
    order: dict[str, int] = {}
    idx = 0

    def add(candidate: str, stop: set[str]) -> None:
        nonlocal idx
        candidate = candidate.strip().lower()
        if len(candidate) < 2 or candidate in stop:
            return
        scores[candidate] += len(candidate)
        if candidate not in order:
            order[candidate] = idx
            idx += 1

    for run in _CJK_RUN.findall(content):
        add(run, _CJK_STOP)
        # 无分词器时, 用 2 字二元组捕捉"公园"这类高频核心词
        if len(run) > 2:
            for i in range(len(run) - 1):
                add(run[i : i + 2], _CJK_STOP)
    for word in _EN_WORD.findall(content):
        add(word, _EN_STOP)

    ranked = sorted(scores, key=lambda w: (-scores[w], order[w]))
    return ranked[:top_n]


def extract_keywords(
    content: str, llm: Optional[LLMClient] = None, top_n: int = 5
) -> list[str]:
    """提取记忆的关键词: 优先 LLM, 失败或未配置则用规则版."""
    if llm is not None and llm.available:
        prompt = (
            "从下面这段记忆中提取 3-6 个关键词(实体/地点/锚点), 只返回 JSON 数组:\n"
            f"记忆: {content}"
        )
        reply = llm.chat([{"role": "user", "content": prompt}])
        parsed = _parse_keyword_list(reply or "")
        if parsed:
            return parsed[:top_n]
    return _rule_extract(content, top_n)
