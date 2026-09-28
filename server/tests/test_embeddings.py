import math
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from server.services.embeddings import embed_chunks
from server.tree import Chunk, token_ids


class EmbeddingTests(unittest.IsolatedAsyncioTestCase):
    async def test_window_pooling_preserves_one_chunk_and_full_input(self):
        chunk = Chunk(node_ids=["n1"], text="one two three four five six seven eight nine ten")
        inputs = []

        async def create(**kwargs):
            inputs.extend(kwargs["input"])
            # Reverse order verifies mapping via response indexes, not list order.
            return SimpleNamespace(data=[SimpleNamespace(index=i, embedding=[3.0, 4.0])
                                         for i in reversed(range(len(kwargs["input"])))])

        client = SimpleNamespace(embeddings=SimpleNamespace(create=AsyncMock(side_effect=create)))
        with patch("server.services.embeddings.MAX_EMBEDDING_TOKENS", 3), \
             patch("server.services.embeddings.EMBEDDING_DIMENSIONS", 2), \
             patch("server.services.embeddings.EMBEDDING_BATCH_SIZE", 2):
            await embed_chunks(client, [chunk])
        self.assertEqual([token for window in inputs for token in window], token_ids(chunk.text))
        self.assertTrue(all(len(window) <= 3 for window in inputs))
        self.assertEqual(chunk.node_ids, ["n1"])
        self.assertAlmostEqual(chunk.embedding[0], 0.6)
        self.assertAlmostEqual(chunk.embedding[1], 0.8)
        self.assertAlmostEqual(math.hypot(*chunk.embedding), 1)

    async def test_incomplete_embedding_response_is_rejected(self):
        client = SimpleNamespace(embeddings=SimpleNamespace(create=AsyncMock(
            return_value=SimpleNamespace(data=[]))))
        with self.assertRaises(RuntimeError):
            await embed_chunks(client, [Chunk(node_ids=["n1"], text="Contract")])
