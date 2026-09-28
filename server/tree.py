"""Server-owned document trees and top-down, sibling-packed chunks."""

from dataclasses import dataclass, field
from typing import TypedDict

import tiktoken

MAX_CHUNK_LENGTH = 700  # Tokens, including the complete ancestor context.
TOKENIZER = tiktoken.get_encoding("cl100k_base")


class TreeNode(TypedDict):
    id: str
    text: str
    children: list["TreeNode"]


@dataclass
class Chunk:
    node_ids: list[str]
    text: str
    embedding: list[float] = field(default_factory=list)


def build_tree(outline: str) -> list[TreeNode]:
    """Assign deterministic, document-local IDs to every node in reading order."""
    roots: list[TreeNode] = []
    parents: list[TreeNode] = []
    node_number = 0
    for line in outline.splitlines():
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent % 2 or indent // 2 > len(parents) or line.lstrip(" ").startswith("\t"):
            raise ValueError("Invalid document structure: expected two-space indentation")
        level = indent // 2
        node_number += 1
        node: TreeNode = {"id": f"n{node_number}", "text": line[indent:], "children": []}
        siblings = roots if level == 0 else parents[level - 1]["children"]
        siblings.append(node)
        parents[level:] = [node]
    if not roots:
        raise ValueError("Document structure is empty")
    return roots


def token_ids(text: str) -> list[int]:
    return TOKENIZER.encode(text, disallowed_special=())


def chunk_tree(tree: list[TreeNode], max_length: int = MAX_CHUNK_LENGTH) -> list[Chunk]:
    """Preserve fitting subtrees, pack adjacent siblings, and descend into oversized (>max_length tokens)
    subtrees. A leaf is indivisible, even when its context exceeds the budget
    (function embed_chunks handles large chunks by windowing and averaging).
    """
    if max_length <= 0:
        raise ValueError("Chunk length must be positive")
    chunks: list[Chunk] = []

    def subtree_text(node: TreeNode, depth: int = 0) -> str:
        return "\n".join([
            "  " * depth + node["text"],
            *(subtree_text(child, depth + 1) for child in node["children"]),
        ])

    def pack(siblings: list[TreeNode], ancestors: list[str]) -> None:
        # ancestor text supplies context, such as Rental Contract > 1) Obligations > ...
        context = " > ".join(ancestors)
        pending: list[TreeNode] = []

        def render(nodes: list[TreeNode]) -> str:
            body = "\n".join(subtree_text(node) for node in nodes)
            return f"{context}\n\n{body}" if context else body

        def emit(nodes: list[TreeNode]) -> None:
            if nodes:
                chunks.append(Chunk(node_ids=[node["id"] for node in nodes], text=render(nodes)))

        for node in siblings:
            if len(token_ids(render([*pending, node]))) <= max_length:
                pending.append(node)
                continue
            emit(pending)
            pending = []
            if len(token_ids(render([node]))) <= max_length:
                pending = [node]
            elif node["children"]:
                pack(node["children"], [*ancestors, node["text"]])
            else:
                emit([node])
        emit(pending)

    pack(tree, [])
    return chunks
