"""
Production RAG - FastAPI backend entry point.
"""
import os
import asyncio
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from config import get_settings
from db.models import init_db
from ingestion.embedder import ensure_collection
from routers.upload import router as upload_router
from routers.query import router as query_router
from routers.ws import router as ws_router

# Configure structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer() if os.getenv("APP_ENV") == "production" else structlog.dev.ConsoleRenderer(),
    ],
)

settings = get_settings()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("starting_up", env=settings.app_env)
    os.makedirs(settings.upload_dir, exist_ok=True)
    
    # Retry database initialization
    retries = 5
    while retries > 0:
        try:
            await init_db()
            logger.info("database_initialized")
            break
        except Exception as e:
            retries -= 1
            logger.error("database_connection_failed", error=str(e), retries_left=retries)
            if retries == 0:
                raise
            await asyncio.sleep(2)

    # Retry vector store initialization
    retries = 5
    while retries > 0:
        try:
            await ensure_collection()
            logger.info("vector_store_initialized")
            break
        except Exception as e:
            retries -= 1
            logger.error("vector_store_connection_failed", error=str(e), retries_left=retries)
            if retries == 0:
                raise
            await asyncio.sleep(2)
            
    yield
    # Shutdown
    logger.info("shutting_down")


app = FastAPI(
    title="Production RAG API",
    version="1.0.0",
    description="Retrieval-Augmented Generation system with hybrid search and streaming",
    lifespan=lifespan,
)

# ─── Middleware ───────────────────────────────────────────────────
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ─────────────────────────────────────────────────────
app.include_router(upload_router)
app.include_router(query_router)
app.include_router(ws_router)


# ─── Health & Info ────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/")
async def root():
    return {
        "name": "Production RAG API",
        "docs": "/docs",
        "health": "/health",
    }
