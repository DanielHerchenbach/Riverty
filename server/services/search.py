"""Plan retrieval, merge candidates, then locate matches in each document tree."""

import json
import logging
import os
from time import perf_counter
from typing import Literal

import psycopg
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from server.services.embeddings import embed_chunks
from server.tree import Chunk, TreeNode

logger = logging.getLogger(__name__)
SEARCH_MODEL = os.environ.get("RIVERTY_SEARCH_MODEL", "gpt-6-sol")
VECTOR_SIMILARITY_THRESHOLD = 0.30  # Cosine similarity; tune against demo queries.
DOCUMENT_ROOT_ID = "document_root"


class DocumentReference(BaseModel):
    hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    ext: str = Field(pattern=r"^[a-z0-9]{1,12}$")
    name: str = Field(min_length=1)


class SearchRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=10000)
    documents: list[DocumentReference] = Field(min_length=1)


class SearchPlan(BaseModel):
    exact_phrases: list[str]
    semantic_queries: list[str]


class NodeMatches(BaseModel):
    matches: list[str]


class DocumentResult(BaseModel):
    hash: str
    ext: str
    matches: list[str]
    status: Literal["evaluated", "no_candidates", "error"]
    error: str | None = None


class SearchResponse(BaseModel):
    plan: SearchPlan
    explanations: list[str]
    documents: list[DocumentResult]


PLANNER_PROMPT = """Plan a search of legal contracts. Return the requested schema.

Each exact phrase and semantic query is searched independently.
Results from all searches are combined by union (OR) and deduplicated:
a match from any search becomes a candidate for final evaluation (which is performed externally).

semantic_queries describe meanings to retrieve; use natural-language phrases, not isolated keywords.
Leave semantic_queries empty if semantic search cannot reliably narrow down the relevant passages.

exact_phrases contain literal text to retrieve; use words or phrases expected to appear in relevant passages.
Matching is case-insensitive.
Leave exact_phrases empty if literal text matching cannot reliably narrow down the relevant passages.

Both semantic_queries and exact_phrases may be empty at the same time.
In this case, the entire document is reviewed by the final evaluation.

Generate a compact set of complementary phrases and semantic queries.
Avoid alternatives already covered by another substring or semantic query.
Add alternatives only when they are likely to retrieve relevant passages otherwise missed.
Preserve the user’s scope.

IMPORTANT:
Prioritize finding all potentially relevant passages, even if this includes some irrelevant ones.
"""

EVALUATOR_PROMPT = rf"""Find matches to the original user search request in the provided legal contract.
The supplied JSON tree contains document text and IDs. Return only {{"matches": ["node_id"]}}.

Choose the smallest sufficient node(s): prefer a leaf when it contains the match,
or a parent when the match needs introductory wording and multiple children.
Do not return a broad section simply because one descendant matches.
Do not return duplicates or both an ancestor and any of its descendants.
Return {{"matches": []}} when nothing satisfies the request.

The document root ID is {DOCUMENT_ROOT_ID}.
Return it only if that ID is present and the document as a whole satisfies the request.
For matches within specific passages, return the smallest sufficient node IDs instead.
"""


async def structured_call(client: AsyncOpenAI, system: str, payload: dict, schema):
    response = await client.chat.completions.parse(
        model=SEARCH_MODEL,
        reasoning_effort="medium",
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        response_format=schema,
    )
    choice = response.choices[0]
    if choice.finish_reason != "stop" or choice.message.parsed is None:
        raise RuntimeError("Search model did not return a complete structured response")
    return choice.message.parsed


def normalize_plan(plan: SearchPlan) -> SearchPlan:
    def unique(values: list[str]) -> list[str]:
        result: dict[str, str] = {}
        for value in values:
            if value.strip():
                result.setdefault(value.strip().casefold(), value.strip())
        return list(result.values())

    phrases = unique(plan.exact_phrases)
    queries = unique(plan.semantic_queries)
    return SearchPlan(exact_phrases=phrases, semantic_queries=queries)


def literal_pattern(phrase: str) -> str:
    # User-supplied % and _ are literal text, not SQL wildcards.
    return "%" + phrase.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def retrieve_candidates(connection, document: DocumentReference, plan: SearchPlan,
                        query_chunks: list[Chunk]) -> set[str]:
    candidates: set[str] = set()
    for phrase in plan.exact_phrases:
        rows = connection.execute(
            "SELECT node_ids FROM chunks WHERE file_hash = %s AND file_ext = %s AND text ILIKE %s",
            (document.hash, document.ext, literal_pattern(phrase)),
        ).fetchall()
        for (ids,) in rows:
            candidates.update(ids)
    for query in query_chunks:
        # No LIMIT, no approximate index, and no dependency on the literal results.
        rows = connection.execute(
            "SELECT node_ids FROM chunks WHERE file_hash = %s AND file_ext = %s "
            "AND 1 - (embedding <=> %s::vector) >= %s",
            (document.hash, document.ext, json.dumps(query.embedding), VECTOR_SIMILARITY_THRESHOLD),
        ).fetchall()
        candidates.update(node_id for (ids,) in rows for node_id in ids)
    return candidates


def candidate_tree(tree: list[TreeNode], name: str, candidates: set[str] | None) -> tuple[dict, set[str]]:
    """Keep retrieved subtrees and ancestor text; only selectable nodes have IDs."""
    selectable: set[str] = set()

    def visit(node: TreeNode, include: bool = False) -> dict | None:
        include = include or candidates is None or node["id"] in candidates
        children = [child for source in node["children"] if (child := visit(source, include)) is not None]
        if not include and not children:
            return None
        complete = include or (len(children) == len(node["children"])
                               and all("id" in child for child in children))
        result = {"text": node["text"], "children": children}
        if complete:
            selectable.add(node["id"])
            result["id"] = node["id"]
        return result

    children = [node for source in tree if (node := visit(source)) is not None]
    root = {"text": name, "children": children}
    if candidates is None:
        selectable.add(DOCUMENT_ROOT_ID)
        root["id"] = DOCUMENT_ROOT_ID
    return root, selectable


def validate_matches(matches: list[str], tree: dict, selectable: set[str]) -> list[str]:
    selected = set(matches)
    if selected - selectable:
        raise ValueError("Search returned IDs outside the supplied selectable nodes")
    result: list[str] = []

    def visit(node: dict) -> None:
        if node.get("id") in selected:
            result.append(node["id"])
        else:
            for child in node["children"]:
                visit(child)

    visit(tree)
    return result


async def search_documents(request: SearchRequest, database_url: str) -> SearchResponse:
    timings: list[tuple[str, float]] = []
    started = perf_counter()
    try:
        return await _search_documents(request, database_url, timings)
    finally:
        rows = sorted(timings, key=lambda row: row[1], reverse=True)
        rows.append(("Total", perf_counter() - started))
        width = max(len(stage) for stage, _ in rows)
        lines = [f"| {'Stage':<{width}} | Time      |", f"| {'-' * width} | --------- |"]
        for stage, seconds in rows:
            duration = f"{seconds:.2f} s" if seconds >= 1 else f"{seconds:.3f} s"
            lines.append(f"| {stage:<{width}} | {duration:>9} |")
        print("\n" + "\n".join(lines), flush=True)


async def _search_documents(request: SearchRequest, database_url: str,
                            timings: list[tuple[str, float]]) -> SearchResponse:
    if not request.prompt.strip():
        raise ValueError("Enter a search prompt")
    documents = list({(doc.hash, doc.ext): doc for doc in request.documents}.values())
    # Read only the explicitly requested documents. No connection stays open over LLM calls.
    trees = {}
    tic = perf_counter()
    with psycopg.connect(database_url) as connection:
        for doc in documents:
            row = connection.execute("SELECT tree FROM files WHERE hash = %s AND ext = %s",
                                     (doc.hash, doc.ext)).fetchone()
            if row is None or not row[0]:
                raise ValueError(f"Document is not ready: {doc.name}")
            trees[(doc.hash, doc.ext)] = row[0]
    timings.append(("Load documents", perf_counter() - tic))

    async with AsyncOpenAI(timeout=600, max_retries=0) as client:
        tic = perf_counter()
        raw_plan = await structured_call(client, PLANNER_PROMPT, {"request": request.prompt}, SearchPlan)
        plan = normalize_plan(raw_plan)
        use_retrieval = bool(plan.exact_phrases or plan.semantic_queries)
        timings.append(("Query planning", perf_counter() - tic))
        query_chunks = [Chunk(node_ids=[], text=query) for query in plan.semantic_queries]
        if query_chunks:
            tic = perf_counter()
            await embed_chunks(client, query_chunks)
            timings.append(("Query embeddings", perf_counter() - tic))

        candidates: dict[tuple[str, str], set[str] | None] = {}
        if use_retrieval:
            tic = perf_counter()
            with psycopg.connect(database_url) as connection:
                for doc in documents:
                    candidates[(doc.hash, doc.ext)] = retrieve_candidates(connection, doc, plan, query_chunks)
            timings.append(("All database retrieval", perf_counter() - tic))

        results: list[DocumentResult] = []
        for doc in documents:
            ids = candidates.get((doc.hash, doc.ext))
            if ids == set():
                results.append(DocumentResult(hash=doc.hash, ext=doc.ext, matches=[], status="no_candidates"))
                continue
            tic = perf_counter()
            try:
                tree, selectable = candidate_tree(trees[(doc.hash, doc.ext)], doc.name, ids)
                answer = await structured_call(client, EVALUATOR_PROMPT, {
                    "original_request": request.prompt,
                    "tree": tree,
                }, NodeMatches)
                matches = validate_matches(answer.matches, tree, selectable)
                results.append(DocumentResult(hash=doc.hash, ext=doc.ext, matches=matches, status="evaluated"))
            except Exception:
                logger.exception("Final search evaluation failed for %s.%s", doc.hash, doc.ext)
                results.append(DocumentResult(hash=doc.hash, ext=doc.ext, matches=[], status="error",
                                              error="Could not review this document; retry the search."))
            finally:
                timings.append((f"Final evaluation: {doc.name}", perf_counter() - tic))

    explanations = []
    if not use_retrieval:
        explanations.append("Full-document review; no text or vector filtering was used.")
    else:
        if plan.exact_phrases:
            explanations.append("Case-insensitive text search for " + " OR ".join(
                f"‘{phrase}’" for phrase in plan.exact_phrases) + ".")
        if plan.semantic_queries:
            explanations.append("Vector search for " + " OR ".join(
                f"‘{query}’" for query in plan.semantic_queries) + ".")
        explanations.append("Combined candidates were reviewed against your original request.")
    reviewed = sum(result.status == "evaluated" for result in results)
    explanations.append(f"Reviewed {reviewed} of {len(documents)} documents.")
    return SearchResponse(plan=plan, explanations=explanations, documents=results)
