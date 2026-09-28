import unittest

from server.tree import build_tree, chunk_tree, token_ids


class TreeTests(unittest.TestCase):
    def test_ids_and_text_preserve_reading_order(self):
        tree = build_tree("Contract\n  Clause\n    First paragraph\n    Second paragraph\n  Next clause")
        self.assertEqual(tree[0]["id"], "n1")
        self.assertEqual(tree[0]["children"][0]["children"][1],
                         {"id": "n4", "text": "Second paragraph", "children": []})
        self.assertEqual(tree[0]["children"][1]["id"], "n5")

    def test_malformed_and_empty_outlines_are_rejected(self):
        for outline in ["", "  Orphan", "Root\n   Bad", "Root\n    Skipped", "Root\n\tBad"]:
            with self.subTest(outline=outline), self.assertRaises(ValueError):
                build_tree(outline)

    def test_whole_fitting_subtree_is_one_chunk(self):
        tree = build_tree("Contract\n  Clause\n    Content")
        chunks = chunk_tree(tree)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].node_ids, ["n1"])
        self.assertIn("Content", chunks[0].text)

    def test_packs_siblings_with_complete_ancestor_context(self):
        tree = build_tree("Contract\n  Conditions\n    Payment overdue\n    Notice delivered\n    " + "long " * 100)
        budget = len(token_ids("Contract > Conditions\n\nPayment overdue\nNotice delivered"))
        chunks = chunk_tree(tree, budget)
        self.assertEqual([chunk.node_ids for chunk in chunks], [["n3", "n4"], ["n5"]])
        self.assertEqual(len(token_ids(chunks[0].text)), budget)
        self.assertTrue(all(chunk.text.startswith("Contract > Conditions\n\n") for chunk in chunks))
        self.assertGreater(len(token_ids(chunks[1].text)), budget)
        self.assertTrue(chunks[1].text.endswith("long " * 100))

    def test_context_counts_against_budget_and_leaves_are_never_split(self):
        tree = build_tree("Very long governing context " * 20 + "\n  First\n  Second")
        chunks = chunk_tree(tree, 10)
        self.assertEqual([chunk.node_ids for chunk in chunks], [["n2"], ["n3"]])
        self.assertTrue(all(len(token_ids(chunk.text)) > 10 for chunk in chunks))

    def test_all_leaves_covered_once_without_cross_parent_packing(self):
        tree = build_tree("Contract\n  A\n    " + "alpha " * 20 + "\n    a\n  B\n    " + "beta " * 20 + "\n    b")
        chunks = chunk_tree(tree, 12)
        self.assertEqual([chunk.node_ids for chunk in chunks], [["n3"], ["n4"], ["n6"], ["n7"]])
        self.assertTrue(chunks[1].text.startswith("Contract > A"))
        self.assertTrue(chunks[3].text.startswith("Contract > B"))
