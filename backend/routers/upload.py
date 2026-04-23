"""
Upload router: POST /api/upload (file) and POST /api/ingest-url
Runs ingestion pipeline asynchronously via background task.
"""
import os
import uuid
import asyncio
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, HttpUrl

from db.models import Document, Chunk, get_db
from ingestion.loader import load_document, detect_type
from ingestion.chunker import chunk_pages
from ingestion.embedder import upsert_chunks, delete_doc_vectors
from config import get_settings
import structlog

router = APIRouter(prefix="/api", tags=["ingest"])
settings = get_settings()
logger = structlog.get_logger()


class UrlIngestRequest(BaseModel):
    url: str
    name: str | None = None


async def run_ingestion(doc_id: str, path: str, is_url: bool = False):
    """Background task: load → chunk → embed → store."""
    from db.models import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        try:
            # Load
            pages = load_document(path)
            if not pages:
                raise ValueError("No content extracted from document")

            # Chunk
            chunks = chunk_pages(pages)
            if not chunks:
                raise ValueError("No chunks produced from document")

            # Embed + upsert to Qdrant
            qdrant_ids = await upsert_chunks(doc_id, chunks)

            # Save chunks to DB
            for chunk, qid in zip(chunks, qdrant_ids):
                db.add(Chunk(
                    document_id=doc_id,
                    chunk_index=chunk["chunk_index"],
                    content=chunk["content"],
                    token_count=chunk.get("token_count", 0),
                    page_number=chunk.get("page"),
                    qdrant_id=qid,
                ))

            # Mark document ready
            result = await db.execute(select(Document).where(Document.id == doc_id))
            doc = result.scalar_one_or_none()
            if doc:
                doc.total_chunks = len(chunks)
                doc.status = "ready"

            await db.commit()
            logger.info("ingestion_complete", doc_id=doc_id, chunks=len(chunks))

        except Exception as e:
            logger.error("ingestion_failed", doc_id=doc_id, error=str(e))
            result = await db.execute(select(Document).where(Document.id == doc_id))
            doc = result.scalar_one_or_none()
            if doc:
                doc.status = "error"
                doc.error_message = str(e)
            await db.commit()


@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    # Validate size
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.max_upload_size_mb:
        raise HTTPException(400, f"File too large: {size_mb:.1f}MB (max {settings.max_upload_size_mb}MB)")

    # Save file
    os.makedirs(settings.upload_dir, exist_ok=True)
    ext = Path(file.filename or "file.txt").suffix
    saved_name = f"{uuid.uuid4()}{ext}"
    saved_path = os.path.join(settings.upload_dir, saved_name)

    with open(saved_path, "wb") as f:
        f.write(content)

    # Create DB record
    file_type = detect_type(file.filename or "")
    doc = Document(
        filename=saved_name,
        original_name=file.filename or saved_name,
        file_type=file_type,
        file_size=len(content),
        status="processing",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    doc_id = str(doc.id)
    background_tasks.add_task(run_ingestion, doc_id, saved_path)

    return {"id": doc_id, "name": file.filename, "status": "processing"}


@router.post("/ingest-url")
async def ingest_url(
    req: UrlIngestRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    doc = Document(
        filename=req.url,
        original_name=req.name or req.url,
        file_type="url",
        file_size=0,
        source_url=req.url,
        status="processing",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    doc_id = str(doc.id)
    background_tasks.add_task(run_ingestion, doc_id, req.url, is_url=True)

    return {"id": doc_id, "name": req.name or req.url, "status": "processing"}


@router.get("/documents")
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    docs = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "name": d.original_name,
            "type": d.file_type,
            "size": d.file_size,
            "status": d.status,
            "chunks": d.total_chunks,
            "created_at": d.created_at.isoformat(),
        }
        for d in docs
    ]


@router.get("/documents/{doc_id}/status")
async def document_status(doc_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    return {"id": doc_id, "status": doc.status, "chunks": doc.total_chunks, "error": doc.error_message}


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    # Remove from Qdrant
    await delete_doc_vectors(doc_id)

    # Remove file if local
    if doc.file_type != "url":
        path = os.path.join(settings.upload_dir, doc.filename)
        if os.path.exists(path):
            os.remove(path)

    await db.delete(doc)
    await db.commit()
    return {"deleted": doc_id}
