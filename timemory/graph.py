"""将记忆块/片段关系渲染为 SVG, 直观展示吸收与融会贯通."""

from __future__ import annotations

import math
from typing import Iterable, Optional

from .models import MemoryBlock


def render_graph(
    keywords: Iterable[str],
    edges: Iterable[tuple[str, str]],
    title: str = "",
    chain: Optional[list[str]] = None,
    note: str = "",
    width: int = 640,
    height: int = 460,
) -> str:
    """渲染关键词图: 节点=关键词, 边=通路片段, 底部标注融会贯通结果."""
    nodes = sorted(set(keywords))
    cx, cy = width / 2, height / 2
    radius = min(width, height) / 2 - 70

    pos: dict[str, tuple[float, float]] = {}
    for i, a in enumerate(nodes):
        angle = 2 * math.pi * i / max(len(nodes), 1) - math.pi / 2
        pos[a] = (cx + radius * math.cos(angle), cy + radius * math.sin(angle))

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="{}" height="{}" '
        'font-family="sans-serif" viewBox="0 0 {w} {h}">'.format(width, height, w=width, h=height)
    ]
    parts.append(
        f'<text x="{width / 2:.1f}" y="26" text-anchor="middle" font-size="16" '
        f'font-weight="bold" fill="#0f172a">{title}</text>'
    )

    # 边(片段通路, 蓝)
    drawn: set[tuple[str, str]] = set()
    for a, b in edges:
        key = tuple(sorted((a, b)))
        if key in drawn:
            continue
        drawn.add(key)
        x1, y1 = pos[a]
        x2, y2 = pos[b]
        parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            'stroke="#3b82f6" stroke-width="2.5"/>'
        )

    # 通路高亮(绿)
    if chain and len(chain) >= 3:
        pts = []
        for a in chain:
            x, y = pos[a]
            pts.append(f"{x:.1f},{y:.1f}")
        parts.append(
            f'<polyline points="{" ".join(pts)}" fill="none" stroke="#16a34a" '
            'stroke-width="3.5" stroke-dasharray="6,3" opacity="0.7"/>'
        )

    # 关键词节点
    for a, (x, y) in pos.items():
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="17" fill="#1e293b" '
            'stroke="#0f172a" stroke-width="1.5"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="middle" font-size="13" '
            f'fill="#ffffff">{a}</text>'
        )

    # 底部说明
    footer = []
    if chain and len(chain) >= 3:
        footer.append(f"融会贯通: {' → '.join(chain)}")
    if note:
        footer.append(note)
    if footer:
        parts.append(
            f'<text x="{width / 2:.1f}" y="{height - 24:.1f}" text-anchor="middle" '
            f'font-size="13" fill="#475569">{"    |    ".join(footer)}</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


def render_blocks(blocks: Iterable[MemoryBlock], title: str = "") -> str:
    """把多个记忆块并排渲染(用于 CLI graph)."""
    items = list(blocks)
    if not items:
        return render_graph([], [], title=title or "(空)")
    panel_w = 320
    width = max(panel_w * len(items), 640)
    height = 420
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="{}" height="{}" '
        'font-family="sans-serif" viewBox="0 0 {w} {h}">'.format(width, height, w=width, h=height)
    ]
    parts.append(
        f'<text x="{width / 2:.1f}" y="24" text-anchor="middle" font-size="16" '
        f'font-weight="bold" fill="#0f172a">{title}</text>'
    )

    for i, block in enumerate(items):
        x0 = i * panel_w + 20
        x1 = (i + 1) * panel_w - 20
        cx = (x0 + x1) / 2
        cy = 220
        # 块边界
        parts.append(
            f'<rect x="{x0:.1f}" y="70" width="{x1 - x0:.1f}" height="300" rx="14" '
            'fill="#f8fafc" stroke="#cbd5e1" stroke-width="1.5"/>'
        )
        parts.append(
            f'<text x="{cx:.1f}" y="98" text-anchor="middle" font-size="13" font-weight="bold" '
            f'fill="#0f172a">{block.id}</text>'
        )
        parts.append(
            f'<text x="{cx:.1f}" y="116" text-anchor="middle" font-size="11" fill="#64748b">'
            f'{", ".join(block.keywords) or "(无关键词)"} · {len(block.sources)} 条片段</text>'
        )
        # 块内关键词小圆
        kws = sorted(set(block.keywords))
        pos: dict[str, tuple[float, float]] = {}
        r = min((x1 - x0) / 2 - 30, 90)
        for j, a in enumerate(kws):
            angle = 2 * math.pi * j / max(len(kws), 1) - math.pi / 2
            pos[a] = (cx + r * math.cos(angle), 210 + r * math.sin(angle))
        drawn: set[tuple[str, str]] = set()
        for pair in block.links:
            if pair[0] not in pos or pair[1] not in pos:
                continue
            key = tuple(sorted(pair))
            if key in drawn:
                continue
            drawn.add(key)
            x1p, y1p = pos[pair[0]]
            x2p, y2p = pos[pair[1]]
            parts.append(
                f'<line x1="{x1p:.1f}" y1="{y1p:.1f}" x2="{x2p:.1f}" y2="{y2p:.1f}" '
                'stroke="#3b82f6" stroke-width="2"/>'
            )
        for a, (x, y) in pos.items():
            parts.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="15" fill="#1e293b"/>'
            )
            parts.append(
                f'<text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="middle" font-size="12" '
                f'fill="#ffffff">{a}</text>'
            )
        # 通路标注
        chain = block.chain
        if chain and len(chain) >= 3:
            parts.append(
                f'<text x="{cx:.1f}" y="352" text-anchor="middle" font-size="12" '
                f'fill="#16a34a">融会贯通: {" → ".join(chain)}</text>'
            )

    parts.append("</svg>")
    return "\n".join(parts)
