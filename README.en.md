# Ti-memory

> Fragment memory · Cross-linkage (Rong Hui Guan Tong) — a fragment-based memory system for LLMs

## Inspiration

Human memory is fragmentary: what we remember is a set of independent paths (A→B, C→B), not a complete map. You have walked A→B and you have walked C→B — both pass through B — yet in your mind they are two unrelated impressions. Until one day you realize A, B, and C are actually connected: A→B→C is one continuous path. That moment is *Rong Hui Guan Tong* (融会贯通) — things click together.

Ti-memory turns this process into a memory system: **independent memory blocks, keyword retrieval, absorptive merging of new memories, and fading of absorbed fragments**.

## Design

- **Memory block**: Memory is stored in independent *blocks*. Each block carries keywords (anchors, e.g. A, B, C) as retrieval entries, and keeps the consolidated description inside.
- **Keyword retrieval**: matching a keyword returns a block overview; **you enter the block to read the full description**.
- **Absorptive cross-linkage**: when a new memory shares a keyword with a block, it is *absorbed* into that block (keyword union, link update, description re-rendered). If a new memory bridges several blocks, they are merged into one larger block. As a result, the total number of blocks grows slowly and does not scale linearly with the number of fragments.
- **Fading**: an absorbed fragment no longer exists as an independent memory; it is kept only as a provenance record with decaying strength (halved every 30 days by default), mimicking the forgetting curve of real memory.
- **Path detection**: when fragments inside a block connect through shared keywords into a path, the system automatically detects and annotates the complete route, e.g. A→B→C.

## Quick Start

Requirements: Python 3.9+

```bash
# Run the demo: A→B and C→B are absorbed into one block, then C→D joins in
# (the block count stays at 1 throughout)
python demo.py

# CLI usage
python cli.py add "walk from A to B" --keywords A B   # add a fragment
python cli.py list                                     # list memory blocks
python cli.py query B                                  # keyword retrieval (overview)
python cli.py get <block_id>                           # enter a block to read the full description
```

`demo.py` generates `demo_output/before.svg` and `after.svg`, showing the transition from "two independent fragments" to "one cross-linked block".

## Optional: LLM-generated descriptions

Without configuration, a deterministic rule-based renderer is used (testable). Set these environment variables to have an LLM generate more natural consolidated descriptions:

```bash
export TI_MEMORY_LLM_BASE_URL=https://api.deepseek.com/v1   # any OpenAI-compatible endpoint
export TI_MEMORY_LLM_API_KEY=sk-xxxx
export TI_MEMORY_LLM_MODEL=deepseek-chat
```

## Project Structure

```
Ti-memory/
├── timemory/            # Core engine
│   ├── models.py        #   MemoryBlock / absorbed Source (decaying)
│   ├── linking.py       #   keyword matching & path detection (A→B→C)
│   ├── synthesis.py     #   absorb, merge, render (rule-based + optional LLM)
│   ├── retrieval.py     #   keyword retrieval (overview)
│   ├── graph.py         #   SVG rendering
│   ├── store.py         #   JSON persistence
│   └── system.py        #   MemorySystem facade
├── cli.py               # Command-line entry
├── demo.py              # Scenario demo
├── tests/               # Unit tests
└── README.en.md         # This file (English)
```

## Tests

```bash
python -m unittest discover -s tests -v
```

## License

To be determined (not yet specified).
