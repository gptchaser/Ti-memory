# Ti-memory

> 片段记忆 · 融会贯通 —— 面向 LLM 的片段式记忆系统

## 灵感

人的记忆是片段化的：我们记住的是一条条独立的通路（A→B、C→B），而不是一张完整的图。你走过 A→B，也走过 C→B，两条路都经过 B，但在你的印象里它们是两件互不相干的事。直到某一天你意识到 A、B、C 其实是连在一起的——A→B→C 是一条完整的通路，那一刻你"融会贯通"了。

Ti-memory 把这个过程变成一套记忆系统：**记忆块独立存储、关键词检索、新记忆吸收融合、被吸收片段淡出**。

## 设计

- **记忆块**：记忆以"块"为单位独立存储。每块带关键词（锚点，如 A、B、C）作为检索入口，块内保存融合后的整体描述。
- **关键词检索**：检索命中关键词 → 返回块概览；**进入块内才能看到整体描述**。
- **吸收式融会贯通**：新记忆与某块共享关键词时，被**吸收**进该块（关键词并集、链接更新、整体描述重新渲染）；若新记忆桥接多个块，则把它们合并成一个大块。因此记忆块的总数增长缓慢，不会随片段数量线性膨胀。
- **淡出**：被吸收的片段不再作为独立记忆存在，只保留为带衰减强度的溯源记录（默认每 30 天强度减半），模仿真实记忆的遗忘曲线。
- **通路识别**：块内片段通过共享关键词连成通路时，自动识别并标注 A→B→C 式的完整路径（如 A→B 与 C→B 吸收后，发现通路 A→B→C）。

## 快速开始

要求：Python 3.9+

```bash
# 跑演示：A→B、C→B 吸收成一个块，再融入 C→D（块总数始终保持 1）
python demo.py

# 命令行使用
python cli.py add "从 A 走到 B" --keywords A B   # 添加片段
python cli.py list                                # 列出记忆块
python cli.py query B                             # 关键词检索(概览)
python cli.py get <block_id>                      # 进入块内看整体描述
```

`demo.py` 会生成 `demo_output/before.svg` 与 `after.svg`，直观展示"两条独立片段 → 一个融会贯通块"的过程。

## 可选：接入大模型生成整体描述

未配置时使用规则版渲染（确定性、可测试）。配置以下环境变量后，融会贯通时由 LLM 生成更自然连贯的整体描述：

```bash
export TI_MEMORY_LLM_BASE_URL=https://api.deepseek.com/v1   # 任意 OpenAI 兼容接口
export TI_MEMORY_LLM_API_KEY=sk-xxxx
export TI_MEMORY_LLM_MODEL=deepseek-chat
```

## 项目结构

```
Ti-memory/
├── timemory/            # 核心引擎
│   ├── models.py        #   记忆块 MemoryBlock / 溯源片段 Source(衰减)
│   ├── linking.py       #   关键词匹配与通路识别(A→B→C)
│   ├── synthesis.py     #   吸收、合并与整体描述渲染(规则版 + 可选 LLM)
│   ├── retrieval.py     #   关键词检索(概览)
│   ├── graph.py         #   SVG 渲染
│   ├── store.py         #   JSON 持久化
│   └── system.py        #   MemorySystem 门面
├── cli.py               # 命令行入口
├── demo.py              # 场景演示
├── tests/               # 单元测试
└── README.md            # 本文件(中文)
```

## 测试

```bash
python -m unittest discover -s tests -v
```

## 许可证

本项目许可证待确定（暂未指定）。
