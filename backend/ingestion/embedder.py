"""
Embedder: generates local sentence-transformers embeddings and upserts vectors to Qdrant.
Handles batching, retries, and stores Qdrant point IDs back to DB.
"""
import uuid
import asyncio
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    VectorParams, Distance, PointStruct,
    PayloadSchemaType, HnswConfigDiff
)
import structlog
from config import get_settings

settings = get_settings()
logger = structlog.get_logger()

_embedder = None
_qdrant: AsyncQdrantClient | None = None
_openai_client = None

def get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import AsyncOpenAI
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client

def get_embedder():
    global _embedder
    if "text-embedding" in settings.embedding_model.lower():
        return None # We use OpenAI client directly
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        logger.info("loading_local_embedding_model", model=settings.embedding_model)
        _embedder = SentenceTransformer(settings.embedding_model)
    return _embedder


def get_qdrant() -> AsyncQdrantClient:
    global _qdrant
    if _qdrant is None:
        _qdrant = AsyncQdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    return _qdrant


async def ensure_collection() -> None:
    client = get_qdrant()
    try:
        collections = await client.get_collections()
        names = [c.name for c in collections.collections]
        if settings.qdrant_collection not in names:
            await client.create_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=VectorParams(
                    size=settings.embedding_dim,
                    distance=Distance.COSINE,
                ),
                hnsw_config=HnswConfigDiff(m=16, ef_construct=200),
            )
            logger.info("qdrant_collection_created", name=settings.qdrant_collection)
    except Exception as e:
        # If it's just a "already exists" error, we can ignore it
        if "already exists" in str(e).lower():
            return
        logger.error("ensure_collection_failed", error=str(e))
        raise


async def embed_texts(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """Embed texts in batches. Returns list of embedding vectors."""
    if "text-embedding" in settings.embedding_model.lower():
        client = get_openai_client()
        # OpenAI handles batching up to certain limits, but we batch manually for safety
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            resp = await client.embeddings.create(
                input=batch_texts,
                model=settings.embedding_model
            )
            all_embeddings.extend([data.embedding for data in resp.data])
        return all_embeddings
    
    embedder = get_embedder()
    
    # encode() can process lists of strings. 
    # Since it's CPU/GPU bound, we run it in a thread.
    embeddings = await asyncio.to_thread(
        embedder.encode,
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True
    )
    
    return embeddings.tolist()


async def upsert_chunks(
    doc_id: str,
    chunks: list[dict],
    batch_size: int = 32,
) -> list[str]:
    """
    Embeds chunks and upserts to Qdrant.
    Returns list of Qdrant point IDs (one per chunk).
    """
    await ensure_collection()
    client = get_qdrant()

    texts = [c["content"] for c in chunks]
    embeddings = await embed_texts(texts, batch_size)

    point_ids = []
    points = []

    for chunk, embedding in zip(chunks, embeddings):
        pid = str(uuid.uuid4())
        point_ids.append(pid)
        points.append(PointStruct(
            id=pid,
            vector=embedding,
            payload={
                "doc_id": doc_id,
                "content": chunk["content"],
                "chunk_index": chunk["chunk_index"],
                "page": chunk.get("page"),
                "token_count": chunk.get("token_count", 0),
                **chunk.get("metadata", {}),
            }
        ))

    # Upsert in batches
    for i in range(0, len(points), batch_size):
        await client.upsert(
            collection_name=settings.qdrant_collection,
            points=points[i:i + batch_size],
        )

    logger.info("chunks_upserted", doc_id=doc_id, count=len(points))
    return point_ids


async def delete_doc_vectors(doc_id: str) -> None:
    """Remove all vectors for a document from Qdrant."""
    await ensure_collection()
    client = get_qdrant()
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    await client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=Filter(
            must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
        ),
    )
    logger.info("vectors_deleted", doc_id=doc_id)
