"""
Hybrid retrieval: dense vector search + BM25 keyword search,
fused using Reciprocal Rank Fusion (RRF).
"""
import math
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, SearchParams
from rank_bm25 import BM25Okapi
from ingestion.embedder import embed_texts, get_qdrant
from config import get_settings
import structlog

settings = get_settings()
logger = structlog.get_logger()


def rrf(rankings: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion across multiple ranked lists."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


async def dense_search(
    query: str,
    top_k: int,
    doc_filter: str | None = None,
) -> list[dict]:
    """Vector similarity search in Qdrant."""
    client = get_qdrant()
    [q_vec] = await embed_texts([query])

    filters = None
    if doc_filter:
        filters = Filter(must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_filter))])

    results = await client.search(
        collection_name=settings.qdrant_collection,
        query_vector=q_vec,
        limit=top_k,
        query_filter=filters,
        with_payload=True,
        search_params=SearchParams(hnsw_ef=128),
    )
    return [
        {
            "id": str(r.id),
            "score": r.score,
            "content": r.payload.get("content", ""),
            "doc_id": r.payload.get("doc_id", ""),
            "chunk_index": r.payload.get("chunk_index", 0),
            "page": r.payload.get("page"),
        }
        for r in results
    ]


async def fetch_all_chunks_for_bm25(doc_filter: str | None = None) -> list[dict]:
    """Scroll Qdrant to get all chunks (for BM25 index)."""
    client = get_qdrant()
    filters = None
    if doc_filter:
        filters = Filter(must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_filter))])

    all_chunks = []
    offset = None

    while True:
        results, next_offset = await client.scroll(
            collection_name=settings.qdrant_collection,
            scroll_filter=filters,
            limit=500,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for r in results:
            all_chunks.append({
                "id": str(r.id),
                "content": r.payload.get("content", ""),
                "doc_id": r.payload.get("doc_id", ""),
                "chunk_index": r.payload.get("chunk_index", 0),
                "page": r.payload.get("page"),
            })
        if next_offset is None:
            break
        offset = next_offset

    return all_chunks


def bm25_search(query: str, chunks: list[dict], top_k: int) -> list[dict]:
    """BM25 search over a list of chunk dicts."""
    if not chunks:
        return []
    tokenized = [c["content"].lower().split() for c in chunks]
    bm25 = BM25Okapi(tokenized)
    scores = bm25.get_scores(query.lower().split())
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    return [
        {**chunks[i], "score": float(s)}
        for i, s in ranked[:top_k]
        if s > 0
    ]


async def hybrid_search(
    query: str,
    top_k: int | None = None,
    doc_filter: str | None = None,
) -> list[dict]:
    """
    Full hybrid search pipeline:
    1. Dense vector search
    2. BM25 keyword search
    3. RRF fusion
    Returns top_k fused results.
    """
    k = top_k or settings.top_k_retrieval
    half_k = max(k // 2, 5)

    # Dense search
    dense_results = await dense_search(query, top_k=half_k * 2, doc_filter=doc_filter)
    logger.info("dense_results", count=len(dense_results))

    # BM25 search
    all_chunks = await fetch_all_chunks_for_bm25(doc_filter)
    bm25_results = bm25_search(query, all_chunks, top_k=half_k * 2)
    logger.info("bm25_results", count=len(bm25_results))

    # Build ranked lists by chunk ID
    dense_ranking = [r["id"] for r in dense_results]
    bm25_ranking = [r["id"] for r in bm25_results]

    # Merge all unique results
    all_by_id: dict[str, dict] = {r["id"]: r for r in dense_results}
    all_by_id.update({r["id"]: r for r in bm25_results})

    # Fuse
    fused = rrf([dense_ranking, bm25_ranking])
    top_ids = [fid for fid, _ in fused[:k]]

    return [all_by_id[fid] for fid in top_ids if fid in all_by_id]
