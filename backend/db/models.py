"""
PostgreSQL models via SQLAlchemy (async).
Stores document metadata, chunks, and query logs.
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Float,
    DateTime, Boolean, ForeignKey, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.ext.asyncio import (
    AsyncSession, create_async_engine, async_sessionmaker
)
from config import get_settings

settings = get_settings()

engine = create_async_engine(settings.postgres_url, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(512), nullable=False)
    original_name = Column(String(512), nullable=False)
    file_type = Column(String(64), nullable=False)
    file_size = Column(Integer, nullable=False)
    source_url = Column(Text, nullable=True)
    total_chunks = Column(Integer, default=0)
    status = Column(String(32), default="processing")  # processing | ready | error
    error_message = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chunks = relationship("Chunk", back_populates="document", cascade="all, delete")
    queries = relationship("QueryLog", back_populates="document")


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"))
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    token_count = Column(Integer, default=0)
    page_number = Column(Integer, nullable=True)
    qdrant_id = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="chunks")


class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(128), nullable=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    retrieved_chunks = Column(Integer, default=0)
    reranked_chunks = Column(Integer, default=0)
    latency_ms = Column(Float, nullable=True)
    from_cache = Column(Boolean, default=False)
    feedback = Column(Integer, nullable=True)  # 1 = thumbs up, -1 = thumbs down
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="queries")


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
