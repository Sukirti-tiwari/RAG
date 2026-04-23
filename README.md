# Production RAG System — 6th Semester Project

A full-stack Retrieval-Augmented Generation (RAG) system with hybrid search, streaming responses, and a modern React UI.

## Architecture

```
Data Sources (PDF/DOCX/CSV/URL)
        ↓
  unstructured.io loader
        ↓
  Recursive text chunker (512 tok, 50 overlap)
        ↓
  Local Sentence-Transformers (all-MiniLM-L6-v2)
        ↓
  Qdrant (vector store) + PostgreSQL (metadata)
        ↓
  Hybrid Search: BM25 + Dense Vector (RRF fusion)
        ↓
  Cohere Rerank (top-20 → top-5)
        ↓
  Prompt builder (numbered citations)
        ↓
  Groq API (streaming via WebSocket)
        ↓
  React + Vite frontend
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.11) |
| Vector DB | Qdrant |
| Metadata DB | PostgreSQL 16 |
| Cache | Redis 7 |
| Embeddings | Local Sentence-Transformers (all-MiniLM-L6-v2) |
| Reranker | Cohere rerank-english-v3.0 |
| LLM | Groq (Llama-3.3-70b-versatile) |
| Frontend | React 18 + Vite + TailwindCSS |
| Containerization | Docker + Docker Compose |

## Project Structure

```
rag-project/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Pydantic settings
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── db/
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   └── redis_cache.py       # Semantic query cache
│   ├── ingestion/
│   │   ├── loader.py            # Multi-format document loader
│   │   ├── chunker.py           # Recursive text splitter
│   │   └── embedder.py          # OpenAI embed + Qdrant upsert
│   ├── retrieval/
│   │   ├── hybrid_search.py     # BM25 + dense vector + RRF
│   │   └── reranker.py          # Cohere rerank
│   ├── generation/
│   │   ├── prompt_builder.py    # Context assembly + citations
│   │   └── llm.py               # Claude API (stream + REST)
│   └── routers/
│       ├── upload.py            # POST /api/upload, /api/ingest-url
│       ├── query.py             # POST /api/query
│       └── ws.py                # WS /api/ws/stream
└── frontend/
    ├── src/
    │   ├── App.jsx              # Root layout
    │   ├── components/
    │   │   ├── ChatWindow.jsx   # Chat UI + input
    │   │   ├── ChatMessage.jsx  # Markdown message + citations
    │   │   ├── SourceCard.jsx   # Collapsible source chunks
    │   │   ├── FileUploader.jsx # Drag-drop + URL ingest
    │   │   └── DocumentList.jsx # Sidebar document list
    │   ├── hooks/
    │   │   ├── useChat.js       # WebSocket streaming + history
    │   │   └── useDocuments.js  # Upload/delete/poll status
    │   └── utils/
    │       └── api.js           # Axios + WebSocket helpers
    ├── Dockerfile
    ├── nginx.conf
    └── vite.config.js
```

## Quick Start

### 1. Clone and configure

```bash
git clone <your-repo-url>
cd rag-project
cp .env.example .env
```

Edit `.env` and fill in your API keys:
- `ANTHROPIC_API_KEY` — get from [console.anthropic.com](https://console.anthropic.com)
- `OPENAI_API_KEY` — get from [platform.openai.com](https://platform.openai.com)
- `COHERE_API_KEY` — get from [dashboard.cohere.com](https://dashboard.cohere.com) (free tier works)

### 2. Run with Docker (recommended)

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/docs
- Qdrant UI: http://localhost:6333/dashboard

### 3. Run locally (development)

**Start infrastructure:**
```bash
docker compose up qdrant postgres redis -d
```

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

## API Reference

### Upload a file
```
POST /api/upload
Content-Type: multipart/form-data
Body: file=<binary>

Response: { "id": "uuid", "name": "file.pdf", "status": "processing" }
```

### Ingest a URL
```
POST /api/ingest-url
{ "url": "https://example.com/paper.pdf", "name": "My Paper" }
```

### Query
```
POST /api/query
{
  "question": "What is the main conclusion?",
  "doc_filter": null,        // optional: filter to one doc_id
  "history": [],             // optional: previous messages
  "use_cache": true
}

Response:
{
  "answer": "The main conclusion is...[1][2]",
  "sources": [{ "citation": 1, "content": "...", "page": 3, "score": 0.94 }],
  "from_cache": false,
  "latency_ms": 1240
}
```

### WebSocket streaming
```
WS /api/ws/stream

Send: { "question": "...", "doc_filter": null, "history": [] }

Receive:
  { "type": "sources", "data": [...] }     // sources first
  { "type": "token",   "data": "Hello " }  // streamed tokens
  { "type": "done",    "data": "" }        // stream complete
  { "type": "error",   "data": "msg" }     // on error
```

### List documents
```
GET /api/documents
```

### Delete document
```
DELETE /api/documents/{doc_id}
```

## Key Design Decisions

### Hybrid Search (BM25 + Dense Vector)
Pure vector search misses exact keyword matches. BM25 handles those well but lacks semantic understanding. We combine both using Reciprocal Rank Fusion (RRF) for the best of both worlds.

### Cohere Reranker
After hybrid retrieval (top-20), we use Cohere's cross-encoder reranker to score each chunk against the query with full attention. This re-orders chunks by true relevance, dramatically improving answer quality.

### Semantic Caching (Redis)
Identical (or near-identical) queries skip the entire retrieval+LLM pipeline and return cached answers. Cache is keyed by SHA-256 of the question + document filter string.

### Streaming via WebSocket
The frontend opens a persistent WebSocket connection. Tokens stream from Claude in real-time, giving sub-100ms time-to-first-token UX. Falls back to REST POST /api/query if WebSocket fails.

### Citation System
Each retrieved chunk is numbered [1], [2], etc. in the prompt. Claude is instructed to cite them inline. The frontend renders clickable source cards showing the original chunk text and confidence score.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | Groq API key | required |
| `COHERE_API_KEY` | Cohere key for reranking | optional |
| `EMBEDDING_MODEL` | Local model name | all-MiniLM-L6-v2 |
| `EMBEDDING_DIM` | Model output dimension | 384 |
| `CHUNK_SIZE` | Tokens per chunk | 512 |
| `CHUNK_OVERLAP` | Overlap between chunks | 50 |
| `TOP_K_RETRIEVAL` | Candidates from hybrid search | 20 |
| `TOP_K_RERANK` | Final chunks after reranking | 5 |
| `LLM_MODEL` | Groq model to use | llama-3.3-70b-versatile |
| `REDIS_CACHE_TTL` | Cache TTL in seconds | 3600 |

## Supported File Types

| Type | Extension | Loader |
|------|-----------|--------|
| PDF | .pdf | PyMuPDF (page-level extraction) |
| Word | .docx | python-docx (paragraph-level) |
| Excel | .xlsx | openpyxl (sheet-level) |
| CSV | .csv | stdlib csv (100-row batches) |
| HTML | .html | BeautifulSoup (text extraction) |
| Text | .txt, .md | direct read |
| Web URL | http/https | requests + BeautifulSoup |

## Troubleshooting

**"No relevant documents found"** — Make sure at least one document is fully ingested (status = "ready") before querying.

**Qdrant connection error** — Ensure Docker is running: `docker compose up qdrant -d`

**Slow first query** — The first query builds the BM25 index from all chunks in Qdrant. Subsequent queries are faster. Use Redis cache for repeated questions.

**Cohere reranker skipped** — If `COHERE_API_KEY` is not set, the system falls back to returning top-N chunks by vector similarity score. This still works well.
# RAG
