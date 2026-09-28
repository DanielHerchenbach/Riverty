from dataclasses import dataclass
from pathlib import Path

from openai import AsyncOpenAI

from server.layout import analyze_layout
from server.services.embeddings import embed_chunks
from server.toc import KEY as OPENAI_KEY
from server.toc import SYSTEM_PROMPT_TOC_SIMPLE
from server.tree import Chunk, TreeNode, build_tree, chunk_tree


@dataclass
class AnalysisResult:
    tree: list[TreeNode]
    chunks: list[Chunk]


async def analyze_document(pdf_path: Path) -> AnalysisResult:
    _, document_text = await analyze_layout(pdf_path=pdf_path)

    async with AsyncOpenAI(api_key=OPENAI_KEY, max_retries=0, timeout=600) as client:
        response = await client.chat.completions.create(
            model="gpt-6-sol",
            reasoning_effort="medium",
            temperature=1,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_TOC_SIMPLE},
                {"role": "user", "content": document_text.replace("\n", " ")},
            ],
        )

        outline = response.choices[0].message.content
        if response.choices[0].finish_reason != "stop" or not outline:
            raise RuntimeError("The model returned an incomplete document structure")
        tree = build_tree(outline)
        chunks = chunk_tree(tree)
        await embed_chunks(client, chunks)
    return AnalysisResult(tree=tree, chunks=chunks)
