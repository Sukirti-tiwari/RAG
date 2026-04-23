"""
Cohere reranker: takes hybrid search results and reranks
them using a cross-encoder model for higher precision.
Falls back to original order if Cohere is unavailable.
"""
import cohere
from config import get_settings
import structlog

settings = get_settings()
logger = structlog.get_logger()

_client: cohere.AsyncClient | None = None


def get_client() -> cohere.AsyncClient:
    global _client
    if _client is None:
        _client = cohere.AsyncClient(api_key=settings.cohere_api_key)
    return _client


async def rerank(
    query: str,
    chunks: list[dict],
    top_n: int | None = None,
) -> list[dict]:
    """
    Rerank chunks using Cohere rerank-english-v3.0.
    Returns top_n chunks sorted by relevance, each with a 'rerank_score'.
    Falls back to original order if API fails.
    """
    n = top_n or settings.top_k_rerank
    if not chunks:
        return []

    if not settings.cohere_api_key or settings.cohere_api_key == "your_cohere_api_key_here":
        logger.warning("cohere_key_missing_fallback")
        return chunks[:n]

    try:
        client = get_client()
        docs = [c["content"] for c in chunks]
        resp = await client.rerank(
            model="rerank-english-v3.0",
            query=query,
            documents=docs,
            top_n=n,
        )
        reranked = []
        for result in resp.results:
            chunk = dict(chunks[result.index])
            chunk["rerank_score"] = result.relevance_score
            reranked.append(chunk)
        logger.info("reranked", input=len(chunks), output=len(reranked))
        return reranked

    except Exception as e:
        logger.error("rerank_error", error=str(e))
        # Fallback: return top-n by original score
        sorted_chunks = sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)
        return sorted_chunks[:n]
