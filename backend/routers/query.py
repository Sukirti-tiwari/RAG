"""
Query router: POST /api/query
Full RAG pipeline: hybrid search → rerank → prompt → Claude.
"""
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from db.models import QueryLog, get_db
from db.redis_cache import get_cached, set_cache
from retrieval.hybrid_search import hybrid_search
from retrieval.reranker import rerank
from generation.prompt_builder import build_messages, extract_sources
from generation.llm import generate
from config import get_settings
import structlog

router = APIRouter(prefix="/api", tags=["query"])
settings = get_settings()
logger = structlog.get_logger()


class QueryRequest(BaseModel):
    question: str
    doc_filter: str | None = None  # filter to a specific doc_id
    history: list[dict] | None = None
    session_id: str | None = None
    use_cache: bool = True


class QueryResponse(BaseModel):
    answer: str
    sources: list[dict]
    from_cache: bool
    latency_ms: float


@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest, db: AsyncSession = Depends(get_db)):
    t0 = time.time()

    # 1. Check cache
    if req.use_cache:
        cached = await get_cached(req.question, req.doc_filter)
        if cached:
            logger.info("cache_hit", question=req.question[:60])
            return QueryResponse(**cached, from_cache=True, latency_ms=round((time.time() - t0) * 1000, 1))

    # 2. Hybrid search
    chunks = await hybrid_search(req.question, doc_filter=req.doc_filter)
    if not chunks:
        raise HTTPException(404, "No relevant documents found. Please upload documents first.")

    # 3. Rerank
    top_chunks = await rerank(req.question, chunks)

    # 4. Build prompt
    system, messages = build_messages(req.question, top_chunks, req.history)

    # 5. Generate
    answer = await generate(system, messages)
    sources = extract_sources(top_chunks)

    latency = round((time.time() - t0) * 1000, 1)

    # 6. Cache result
    result_dict = {"answer": answer, "sources": sources}
    if req.use_cache:
        await set_cache(req.question, result_dict, req.doc_filter)

    # 7. Log to DB
    db.add(QueryLog(
        session_id=req.session_id,
        question=req.question,
        answer=answer,
        retrieved_chunks=len(chunks),
        reranked_chunks=len(top_chunks),
        latency_ms=latency,
        from_cache=False,
    ))
    await db.commit()

    logger.info("query_complete", latency_ms=latency, sources=len(sources))
    return QueryResponse(answer=answer, sources=sources, from_cache=False, latency_ms=latency)


@router.post("/feedback")
async def submit_feedback(
    query_id: str,
    rating: int,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    result = await db.execute(select(QueryLog).where(QueryLog.id == query_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(404)
    log.feedback = rating
    await db.commit()
    return {"ok": True}
