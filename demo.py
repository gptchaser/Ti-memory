"""演示 Ti-memory 的核心理念: 吸收、融会贯通、自动提取、遗忘.

场景:
  1. 记下 A→B 的通路 -> 新建一个记忆块
  2. 记下 C→B 的通路 -> 共享关键词 B, 被吸收进块: 块变成 {A,B,C},
     通路 A→B→C; 原来的 A→B 片段不再独立存在(淡出)
  3. 记下 C→D 的通路 -> 因含 C 融入同一块: 通路 A→B→C→D, 块总数不变
  4. 关键词检索 -> 命中块(概览); 进入块内查看整体描述
  5. 不传关键词直接输入 -> 自动提取关键词
  6. 记忆统计: 块总数 vs 片段总数
  7. 遗忘与归档: 长期不用的块变弱, prune 归档

运行: python demo.py
产物: demo_output/before.svg 与 after.svg
"""

from __future__ import annotations

import time
from pathlib import Path

from timemory import JsonStore, MemorySystem
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
    # 每次运行从干净状态开始(演示数据可重复生成)
    demo_store = OUT_DIR / "demo_memories.json"
    JsonStore(str(demo_store)).save([])
    system = MemorySystem(str(demo_store))

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

    print("\n=== 5. 关键词自动提取(不传 keywords, 规则兜底) ===")
    r = system.add("Every morning I ride my bike from home to the office.")
    print(f"  自动提取关键词: {r.block.keywords}")
    print(f"  新建记忆块 {r.block.id} (与前面的块无共享关键词, 保持独立)")

    print("\n=== 6. 记忆统计: 块总数 vs 片段总数 ===")
    s = system.stats()
    print(f"  记忆块: {s['blocks']}  |  片段: {s['fragments']}  |  通路: {s['chains']}")
    print(f"  -> {s['fragments']} 条片段只形成 {s['blocks']} 个块, 吸收式融合让总数不膨胀")

    print("\n=== 7. 遗忘与归档: 长期不用的块会变弱, 可归档清理 ===")
    fading_store = OUT_DIR / "fading_demo.json"
    fading_archive = OUT_DIR / "fading_archive.json"
    store = JsonStore(str(fading_store))
    store.save([])
    fsys = MemorySystem(str(fading_store))
    fsys.add("很久以前在 X 地的一段记忆。", ["X", "Y"])
    blocks = store.load()
    blocks[0].updated_at = time.time() - 200 * 86400  # 模拟 200 天未使用
    store.save(blocks)
    fsys = MemorySystem(str(fading_store))
    old = fsys.blocks[0]
    print(f"  200 天未使用: 强度从 1.00 衰减到 {old.effective_strength():.3f}")
    weak = fsys.prune(threshold=0.2, archive_path=str(fading_archive))
    print(f"  prune 归档 {len(weak)} 个弱块; 活跃块剩余 {len(fsys.blocks)}")
    print(f"  归档文件: {fading_archive} (归档而非删除, 可追溯)")

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
