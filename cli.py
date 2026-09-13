"""Ti-memory 命令行入口.

用法示例:
  python cli.py add "每天从 A 走到 B" --keywords A B
  python cli.py list
  python cli.py query B
  python cli.py get <block_id>
  python cli.py graph graph.svg
"""

from __future__ import annotations

import argparse
import sys

from timemory import MemorySystem
from timemory.graph import render_blocks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ti-memory",
        description="片段记忆 · 融会贯通 —— 面向 LLM 的片段式记忆系统",
    )
    parser.add_argument(
        "--store",
        default="data/memories.json",
        help="记忆存储文件路径 (默认 data/memories.json)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="添加一条记忆片段(共享关键词则被吸收进已有块)")
    p_add.add_argument("content", help="记忆内容")
    p_add.add_argument("--keywords", nargs="+", default=[], help="关键词列表(检索入口)")

    sub.add_parser("list", help="列出所有记忆块(概览)")

    p_query = sub.add_parser("query", help="按关键词检索记忆块(返回概览)")
    p_query.add_argument("tokens", nargs="+", help="检索关键词")

    p_get = sub.add_parser("get", help="进入记忆块, 查看整体描述与溯源片段")
    p_get.add_argument("block_id", help="记忆块 id")

    p_graph = sub.add_parser("graph", help="将记忆块渲染为 SVG")
    p_graph.add_argument("output", nargs="?", default="graph.svg")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    system = MemorySystem(args.store)

    if args.command == "add":
        result = system.add(args.content, args.keywords)
        block = result.block
        if result.created:
            print(f"新建记忆块 {block.id}: {block.content}")
        elif result.merged_blocks:
            print(
                f"桥接合并 {len(result.merged_blocks)} 个块 -> 新块 {block.id}: "
                f"{block.content}"
            )
        else:
            print(f"吸收进已有块 {block.id} (片段已淡出, 只留溯源): {block.content}")
        print(f"  关键词: {', '.join(block.keywords) or '(无)'}  记忆块总数: {len(system.blocks)}")
        if block.chain and len(block.chain) >= 3:
            print(f"  融会贯通通路: {' → '.join(block.chain)}")
    elif args.command == "list":
        if not system.blocks:
            print("(空)")
        for b in system.blocks:
            first = b.content.split("\n", 1)[0]
            print(f"[块] {b.id}  关键词={b.keywords}  片段数={len(b.sources)}")
            print(f"  {first}")
    elif args.command == "query":
        results = system.query(args.tokens)
        if not results:
            print("无命中")
        for r in results:
            print(f"[命中] {r['id']}  关键词={r['keywords']}  片段数={r['n_sources']}")
            print(f"  {r['preview']}  (get {r['id']} 查看整体描述)")
    elif args.command == "get":
        block = system.get(args.block_id)
        if block is None:
            print(f"未找到记忆块: {args.block_id}")
            return 1
        print(f"记忆块 {block.id}  关键词: {', '.join(block.keywords) or '(无)'}")
        print("---- 整体描述 ----")
        print(block.content)
        if block.chain and len(block.chain) >= 3:
            print(f"融会贯通通路: {' → '.join(block.chain)}")
        print("---- 溯源片段(已淡出, 强度随时间衰减) ----")
        for s in block.sources:
            print(f"  [{s.id}] 强度={s.effective_strength():.2f}  关键词={s.keywords}")
            print(f"      {s.content}")
    elif args.command == "graph":
        svg = render_blocks(system.blocks, title="Ti-memory 记忆块")
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"已写入 {args.output} ({len(system.blocks)} 个记忆块)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
