"""演示 Ti-memory 的核心理念: 片段如何被吸收、融会贯通、整体描述.

场景:
  1. 记下 A→B 的通路 -> 新建一个记忆块
  2. 记下 C→B 的通路 -> 与块共享关键词 B, 被吸收进块:
     块变成 {A, B, C}, 通路 A→B→C; 原来的 A→B 片段不再独立存在(淡出)
  3. 记下 C→D 的通路 -> 因含 C 融入同一块:
     块变成 {A, B, C, D}, 通路 A→B→C→D, 记忆块总数始终只有 1 个
  4. 关键词检索 -> 命中块(概览); 进入块内查看整体描述

运行: python demo.py
产物: demo_output/before.svg 与 after.svg
"""

from __future__ import annotations

from pathlib import Path

from timemory import MemorySystem
from timemory.graph import render_graph

OUT_DIR = Path("demo_output")


def show_block(system: MemorySystem, label: str) -> None:
    block = system.blocks[0]
    print(f"  -> 记忆块总数: {len(system.blocks)}")
    print(f"     关键词: {', '.join(block.keywords)}")
    print(f"     整体描述: {block.content!r}")
    if block.chain and len(block.chain) >= 3:
        print(f"     融会贯通通路: {' → '.join(block.chain)}")


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    system = MemorySystem(str(OUT_DIR / "demo_memories.json"))

    print("=== 1. 记下 A→B 的通路(新建记忆块) ===")
    system.add("每天从 A 出发, 沿着河边小路走到 B, 大概二十分钟。", ["A", "B"])
    show_block(system, "")

    print("\n=== 2. 记下 C→B 的通路(共享 B, 被吸收进同一块) ===")
    system.add("从 C 出发, 穿过山谷就能到 B, 一路风景很好。", ["C", "B"])
    show_block(system, "")
    block = system.blocks[0]
    print("  -> 原来的 A→B 片段不再独立存在, 只作为溯源记录(强度将随时间衰减):")
    for s in block.sources:
        print(f"     强度 {s.effective_strength():.2f} | {s.content}")

    print("\n=== 3. 记下 C→D 的通路(因含 C 融入同一块, 总数不变) ===")
    system.add("从 C 继续往 D 走, 翻过一座小山坡就到了。", ["C", "D"])
    show_block(system, "")

    print("\n=== 4. 关键词检索: 命中块(概览), 进入块内看整体描述 ===")
    for token in ["B", "D"]:
        print(f"  query({token}):")
        for r in system.query([token]):
            print(f"    命中块 {r['id']}  关键词={r['keywords']}")
            print(f"    概览: {r['preview']}")
    block = system.blocks[0]
    print(f"  get({block.id}) 进入块内:")
    print(f"    {block.content}")

    # 图形: 吸收前(两条独立片段) vs 吸收后(一个记忆块, 一条通路)
    before = render_graph(
        ["A", "B", "C"],
        [("A", "B"), ("C", "B")],
        title="吸收前: A→B 与 C→B 是两条独立片段",
        note="两个片段互不知晓, 各自独立",
    )
    after = render_graph(
        block.keywords,
        [tuple(p) for p in block.links],
        title="吸收后: 融会贯通为一个记忆块",
        chain=block.chain,
        note=f"1 个记忆块 · {len(block.sources)} 条片段 · 通路 A → B → C → D",
    )
    (OUT_DIR / "before.svg").write_text(before, encoding="utf-8")
    (OUT_DIR / "after.svg").write_text(after, encoding="utf-8")
    print(f"\n图形已输出到 {OUT_DIR / 'before.svg'} 与 {OUT_DIR / 'after.svg'}")


if __name__ == "__main__":
    main()
