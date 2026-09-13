"""Ti-memory 单元测试. 运行: python -m unittest discover -s tests -v"""

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from timemory import MemorySystem
from timemory.linking import chain_path, match_blocks
from timemory.models import MemoryBlock, Source, normalize_keywords
from timemory.synthesis import absorb, create_block, rule_based_render


class TestKeywords(unittest.TestCase):
    def test_normalize_dedup_and_order(self):
        self.assertEqual(normalize_keywords(["A", " B ", "A", "", "C"]), ["A", "B", "C"])


class TestLinking(unittest.TestCase):
    def test_chain_path_discovers_a_b_c(self):
        self.assertEqual(
            chain_path(["A", "B", "C"], [("A", "B"), ("C", "B")]),
            ["A", "B", "C"],
        )

    def test_chain_path_with_branch_returns_none(self):
        edges = [("A", "B"), ("C", "B"), ("D", "B")]
        self.assertIsNone(chain_path(["A", "B", "C", "D"], edges))

    def test_match_blocks_by_shared_keyword(self):
        b1 = MemoryBlock("x", ["A", "B"])
        b2 = MemoryBlock("y", ["C", "D"])
        self.assertEqual(match_blocks([b1, b2], ["B"]), [b1])
        self.assertEqual(match_blocks([b1, b2], ["E"]), [])


class TestSynthesis(unittest.TestCase):
    def test_create_block_seeds_source(self):
        block = create_block("从 A 到 B", ["A", "B"])
        self.assertEqual(block.keywords, ["A", "B"])
        self.assertEqual(len(block.sources), 1)
        self.assertIn("从 A 到 B", block.content)

    def test_absorb_merges_keywords_and_tracks_source(self):
        block = create_block("A 到 B", ["A", "B"])
        absorb(block, "C 到 B", ["C", "B"])
        self.assertEqual(block.keywords, ["A", "B", "C"])
        self.assertEqual(len(block.sources), 2)
        self.assertEqual(block.chain, ["A", "B", "C"])
        self.assertIn("A → B → C", block.content)

    def test_absorb_keeps_fragment_out_of_standalone(self):
        block = create_block("A 到 B", ["A", "B"])
        absorb(block, "C 到 B", ["C", "B"])
        # 被吸收片段只存在于 sources, 不再作为独立块
        self.assertEqual(len(block.sources), 2)
        contents = [s.content for s in block.sources]
        self.assertIn("C 到 B", contents)

    def test_rule_based_render_has_chain(self):
        s1 = Source("A 到 B", ["A", "B"])
        s2 = Source("C 到 B", ["C", "B"])
        out = rule_based_render([s1, s2], ["A", "B", "C"])
        self.assertIn("[1]", out)
        self.assertIn("A → B → C", out)

    def test_source_strength_decays(self):
        old = Source("很久以前的记忆", ["X"], absorbed_at=time.time() - 30 * 86400)
        fresh = Source("刚吸收的记忆", ["Y"])
        self.assertAlmostEqual(old.effective_strength(), 0.5, places=2)
        self.assertGreater(fresh.effective_strength(), old.effective_strength())


class TestSystem(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = str(Path(self.tmp.name) / "mem.json")
        self.sys = MemorySystem(self.store)

    def tearDown(self):
        self.tmp.cleanup()

    def test_new_fragment_creates_block(self):
        r = self.sys.add("A 到 B", ["A", "B"])
        self.assertTrue(r.created)
        self.assertEqual(len(self.sys.blocks), 1)

    def test_related_fragment_absorbs_not_grows(self):
        self.sys.add("A 到 B", ["A", "B"])
        r = self.sys.add("C 到 B", ["C", "B"])
        self.assertFalse(r.created)
        self.assertEqual(len(self.sys.blocks), 1)
        block = self.sys.blocks[0]
        self.assertEqual(sorted(block.keywords), ["A", "B", "C"])
        self.assertEqual(block.chain, ["A", "B", "C"])

    def test_chain_grows_with_c_d(self):
        self.sys.add("A 到 B", ["A", "B"])
        self.sys.add("C 到 B", ["C", "B"])
        self.sys.add("C 到 D", ["C", "D"])
        self.assertEqual(len(self.sys.blocks), 1)
        block = self.sys.blocks[0]
        self.assertEqual(block.chain, ["A", "B", "C", "D"])
        self.assertEqual(len(block.sources), 3)

    def test_bridging_fragment_merges_blocks(self):
        self.sys.add("A 到 B", ["A", "B"])
        self.sys.add("X 到 Y", ["X", "Y"])
        self.assertEqual(len(self.sys.blocks), 2)
        r = self.sys.add("B 到 X", ["B", "X"])
        self.assertEqual(len(self.sys.blocks), 1)
        self.assertEqual(len(r.merged_blocks), 2)
        block = self.sys.blocks[0]
        self.assertEqual(sorted(block.keywords), ["A", "B", "X", "Y"])
        self.assertEqual(len(block.sources), 3)

    def test_query_and_get(self):
        self.sys.add("A 到 B", ["A", "B"])
        self.sys.add("C 到 B", ["C", "B"])
        hits = self.sys.query(["B"])
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["keywords"], ["A", "B", "C"])
        block = self.sys.get(hits[0]["id"])
        self.assertIsNotNone(block)
        self.assertIn("A → B → C", block.content)

    def test_query_by_absorbed_keyword_still_hits(self):
        self.sys.add("A 到 B", ["A", "B"])
        self.sys.add("C 到 D", ["C", "D"])  # 新块
        hits = self.sys.query(["D"])
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["keywords"], ["C", "D"])

    def test_persistence_roundtrip(self):
        self.sys.add("A 到 B", ["A", "B"])
        self.sys.add("C 到 B", ["C", "B"])
        reloaded = MemorySystem(self.store)
        self.assertEqual(len(reloaded.blocks), 1)
        block = reloaded.blocks[0]
        self.assertEqual(sorted(block.keywords), ["A", "B", "C"])
        self.assertEqual(len(block.sources), 2)


if __name__ == "__main__":
    unittest.main()
