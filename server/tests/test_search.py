import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import psycopg
from dotenv import load_dotenv

from server.services.search import (
    DOCUMENT_ROOT_ID, DocumentReference, NodeMatches, SearchPlan, SearchRequest,
    candidate_tree, normalize_plan, retrieve_candidates, search_documents, validate_matches,
)
from server.tree import Chunk, build_tree


class SearchTreeTests(unittest.TestCase):
    def setUp(self):
        self.tree = build_tree("Agreement\n  Payment\n    Pay within 30 days\n  Termination\n    Give notice")

    def test_candidates_keep_context_and_exclude_unretrieved_siblings(self):
        tree, allowed = candidate_tree(self.tree, "contract.pdf", {"n3"})
        self.assertEqual(tree["text"], "contract.pdf")
        self.assertNotIn("id", tree)
        self.assertNotIn("id", tree["children"][0])
        self.assertNotIn("context_only", str(tree))
        self.assertEqual(tree["children"][0]["children"][0]["children"][0]["text"], "Pay within 30 days")
        self.assertEqual(allowed, {"n2", "n3"})
        self.assertEqual(validate_matches(["n3"], tree, allowed), ["n3"])
        for invalid in ["n1", "n4", DOCUMENT_ROOT_ID, "invented"]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate_matches([invalid], tree, allowed)

    def test_full_scan_supports_root_and_removes_overlapping_matches(self):
        tree, allowed = candidate_tree(self.tree, "contract.pdf", None)
        self.assertEqual(tree["id"], DOCUMENT_ROOT_ID)
        self.assertNotIn("context_only", str(tree))
        self.assertEqual(validate_matches(["n3", "n2", "n3"], tree, allowed), ["n2"])
        self.assertEqual(validate_matches(["n3", DOCUMENT_ROOT_ID], tree, allowed), [DOCUMENT_ROOT_ID])
        self.assertEqual(allowed, {DOCUMENT_ROOT_ID, "n1", "n2", "n3", "n4", "n5"})

    def test_plan_normalization_removes_blank_and_duplicate_queries(self):
        plan = normalize_plan(SearchPlan(exact_phrases=[" ", " Payment ", "payment"],
                                         semantic_queries=[" ", "Notice", "notice"]))
        self.assertEqual(plan.model_dump(), {"exact_phrases": ["Payment"], "semantic_queries": ["Notice"]})


class SearchFlowTests(unittest.IsolatedAsyncioTestCase):
    async def run_search(self, plan, answers, candidates=None):
        documents = [DocumentReference(hash=key * 64, ext="pdf", name=f"{key}.pdf") for key in ["a", "b"]]
        request = SearchRequest(prompt="Find missing confidentiality clauses", documents=documents)
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.execute.return_value.fetchone.return_value = (build_tree("Contract\n  Payment terms"),)
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        calls = AsyncMock(side_effect=[plan, *answers])
        with patch("server.services.search.psycopg.connect", return_value=connection), \
             patch("server.services.search.AsyncOpenAI", return_value=client), \
             patch("server.services.search.structured_call", calls), \
             patch("server.services.search.retrieve_candidates", side_effect=candidates) as retrieve, \
             patch("server.services.search.embed_chunks", new_callable=AsyncMock) as embed:
            result = await search_documents(request, "unused")
        return result, calls, retrieve, embed

    async def test_full_scan_reviews_every_document_without_retrieval(self):
        result, calls, retrieve, embed = await self.run_search(
            SearchPlan(exact_phrases=[], semantic_queries=[]),
            [NodeMatches(matches=[DOCUMENT_ROOT_ID]), NodeMatches(matches=[])],
        )
        self.assertEqual([doc.status for doc in result.documents], ["evaluated", "evaluated"])
        self.assertEqual(result.documents[0].matches, [DOCUMENT_ROOT_ID])
        self.assertEqual(calls.await_count, 3)
        retrieve.assert_not_called()
        embed.assert_not_awaited()
        self.assertNotIn("complete_document", calls.await_args_list[1].args[2])
        self.assertNotIn("selectable_ids", calls.await_args_list[1].args[2])

    async def test_retrieval_skips_unmatched_documents_and_flags_bad_ids(self):
        with self.assertLogs("server.services.search", level="ERROR"):
            result, calls, _, _ = await self.run_search(
                SearchPlan(exact_phrases=["Payment"], semantic_queries=[]),
                [NodeMatches(matches=["invented"])], candidates=[{"n2"}, set()],
            )
        self.assertEqual([doc.status for doc in result.documents], ["error", "no_candidates"])
        self.assertEqual(calls.await_count, 2)
        self.assertNotIn("selectable_ids", calls.await_args_list[1].args[2])


class RetrievalDatabaseTests(unittest.TestCase):
    def test_literal_escaping_and_vector_union_without_top_k(self):
        load_dotenv("server/.env")
        database_url = os.environ.get("RIVERTY_DATABASE_URL")
        if not database_url:
            self.skipTest("RIVERTY_DATABASE_URL is not configured")
        doc = DocumentReference(hash="a" * 64, ext="pdf", name="a.pdf")
        with psycopg.connect(database_url) as connection:
            with connection.transaction(force_rollback=True):
                # Temporary table shadows real chunks; nothing persists after the test.
                connection.execute("CREATE TEMP TABLE chunks (file_hash text, file_ext text, "
                                   "node_ids text[], text text, embedding vector(2)) ON COMMIT DROP")
                for number in range(12):
                    connection.execute("INSERT INTO chunks VALUES (%s, 'pdf', %s, 'semantic only', '[1,0]')",
                                       (doc.hash, [f"n{number}"]))
                connection.execute("INSERT INTO chunks VALUES (%s, 'pdf', ARRAY['literal'], 'FEE 10%%_X', '[0,1]')", (doc.hash,))
                connection.execute("INSERT INTO chunks VALUES (%s, 'pdf', ARRAY['wrong'], 'fee 100xX', '[0,1]')", (doc.hash,))
                connection.execute("INSERT INTO chunks VALUES ('other', 'pdf', ARRAY['other'], 'fee 10%%_X', '[1,0]')")
                plan = SearchPlan(exact_phrases=["fee 10%_x"], semantic_queries=["semantic"])
                matches = retrieve_candidates(connection, doc, plan, [Chunk(node_ids=[], text="semantic", embedding=[1, 0])])
                self.assertEqual(matches, {"literal", *(f"n{i}" for i in range(12))})
