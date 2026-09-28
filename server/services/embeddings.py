"""Embed stored chunks, retaining even leaves beyond the model input limit."""

import math

from openai import AsyncOpenAI

from server.tree import Chunk, token_ids

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536  # Must match schema.sql.
MAX_EMBEDDING_TOKENS = 8191
EMBEDDING_BATCH_SIZE = 32


async def embed_chunks(client: AsyncOpenAI, chunks: list[Chunk]) -> None:
    windows: list[tuple[int, list[int]]] = []
    for index, chunk in enumerate(chunks):
        tokens = token_ids(chunk.text)
        if not tokens:
            raise ValueError("Cannot embed an empty chunk")
        windows.extend((index, tokens[start:start + MAX_EMBEDDING_TOKENS])
                       for start in range(0, len(tokens), MAX_EMBEDDING_TOKENS))

    sums = [[0.0] * EMBEDDING_DIMENSIONS for _ in chunks]
    for start in range(0, len(windows), EMBEDDING_BATCH_SIZE):
        batch = windows[start:start + EMBEDDING_BATCH_SIZE]
        response = await client.embeddings.create(
            model=EMBEDDING_MODEL,
            dimensions=EMBEDDING_DIMENSIONS,
            input=[tokens for _, tokens in batch],
            encoding_format="float",
        )
        results = sorted(response.data, key=lambda item: item.index)
        if [item.index for item in results] != list(range(len(batch))):
            raise RuntimeError("Embedding response did not cover every input")
        for item, (chunk_index, tokens) in zip(results, batch):
            if len(item.embedding) != EMBEDDING_DIMENSIONS:
                raise RuntimeError("Unexpected embedding dimensions")
            for dimension, value in enumerate(item.embedding):
                # Large chunks (greater than MAX_EMBEDDING_TOKENS) consist of more than one window.
                # For those, each window contributes to the average embedding weighted by the window length
                # (i.e. number of tokens of the respective window).
                # Sum is normalized below.
                sums[chunk_index][dimension] += value * len(tokens)

    for chunk, values in zip(chunks, sums):
        norm = math.sqrt(sum(value * value for value in values))
        if not math.isfinite(norm) or norm == 0:
            raise RuntimeError("Invalid embedding vector")
        chunk.embedding = [value / norm for value in values]
