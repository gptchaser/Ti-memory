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
- **Automatic keyword extraction**: add a memory without keywords and the system extracts them automatically (via LLM when configured; otherwise a rule-based fallback: high-frequency Chinese runs/bigrams or English word frequency).
- **Anti-bloating**: if a new fragment's keywords are fully covered by one block, it is absorbed only into the strongest block — no redundant merging. Merging happens only for fragments that genuinely bridge multiple blocks.
- **Forgetting**: block strength decays over time (30-day half-life by default) and is reinforced by retrieval/access (use it or lose it); very weak blocks can be archived with `prune` (archived, never deleted, fully traceable).

## Live Demo

Open the [Ti-memory showcase page](https://gptchaser.github.io/Ti-memory/) to try it online: the interactive demo simulates absorption, merging and path detection in the browser, behaving the same as the Python engine. Page source lives in `docs/`.

## Quick Start

Requirements: Python 3.9+

```bash
# Run the demo: A→B and C→B are absorbed into one block, then C→D joins in
# (the block count stays at 1 throughout)
python demo.py

# CLI usage
python cli.py add "walk from A to B" --keywords A B   # add a fragment
python cli.py add "I ride my bike to work every day"  # no keywords: auto-extract
python cli.py list                                     # list memory blocks
python cli.py stats                                    # memory stats (blocks vs fragments)
python cli.py query B                                  # keyword retrieval (overview + related blocks)
python cli.py get <block_id>                           # enter a block to read the full description
python cli.py prune --threshold 0.2                    # archive weak/forgotten blocks
```

`demo.py` walks through: fragment absorption & fading, cross-linked paths, automatic keyword extraction, block-count statistics, and forgetting/archiving. It also generates `demo_output/before.svg` and `after.svg`.

## Optional: LLM-generated descriptions

Without configuration, a deterministic rule-based renderer is used (testable). Set these environment variables to have an LLM generate more natural consolidated descriptions and to extract keywords when `add` is called without them:

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
│   ├── extract.py       #   automatic keyword extraction (optional LLM + rule fallback)
│   ├── synthesis.py     #   absorb, merge, render (rule-based + optional LLM)
│   ├── retrieval.py     #   keyword retrieval (overview)
│   ├── graph.py         #   SVG rendering
│   ├── store.py         #   JSON persistence
│   └── system.py        #   MemorySystem facade
├── cli.py               # Command-line entry
├── demo.py              # Scenario demo
├── docs/                # Showcase page source (GitHub Pages)
├── tests/               # Unit tests
└── README.en.md         # This file (English)
```

## Tests

```bash
python -m unittest discover -s tests -v
```

## License

To be determined (not yet specified).
