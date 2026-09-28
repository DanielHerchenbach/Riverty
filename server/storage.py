"""Atomically persist a tree and its embeddings, including concurrent requests."""

import json

import psycopg
from psycopg.types.json import Jsonb

from server.tree import Chunk, TreeNode


def save_analysis(
    connection: psycopg.Connection,
    file_hash: str,
    ext: str,
    tree: list[TreeNode],
    chunks: list[Chunk],
) -> list[TreeNode]:
    # The caller owns the transaction. Only the first completed analysis wins.
    row = connection.execute(
        "UPDATE files SET tree = %s WHERE hash = %s AND ext = %s AND tree IS NULL RETURNING tree",
        (Jsonb(tree), file_hash, ext),
    ).fetchone()
    if row is not None:
        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO chunks (file_hash, file_ext, node_ids, text, embedding) "
                "VALUES (%s, %s, %s, %s, %s::vector)",
                [(file_hash, ext, chunk.node_ids, chunk.text, json.dumps(chunk.embedding))
                 for chunk in chunks],
            )
        return row[0]
    row = connection.execute(
        "SELECT tree FROM files WHERE hash = %s AND ext = %s", (file_hash, ext)
    ).fetchone()
    if row is None or row[0] is None:
        raise RuntimeError("Could not save the analysis result")
    return row[0]
