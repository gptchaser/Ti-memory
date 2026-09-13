"""JSON 持久化存储(记忆块列表)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Union

from .models import MemoryBlock


class JsonStore:
    """将记忆块列表读写到 JSON 文件, 默认位于项目 data/ 目录."""

    def __init__(self, path: Union[str, Path] = "data/memories.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[MemoryBlock]:
        if not self.path.exists():
            return []
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return [MemoryBlock.from_dict(item) for item in data]

    def save(self, blocks: Iterable[MemoryBlock]) -> None:
        payload = [b.to_dict() for b in blocks]
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
