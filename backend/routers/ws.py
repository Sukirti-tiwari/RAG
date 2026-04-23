"""
WebSocket router: WS /api/ws/stream
Streams LLM tokens in real-time for a responsive chat UX.
Protocol:
  Client sends: {"question": "...", "doc_filter": null, "history": [], "session_id": "..."}
  Server sends: {"type": "sources", "data": [...]}
                {"type": "token", "data": "..."}   (repeated)
                {"type": "done", "data": ""}
                {"type": "error", "data": "message"}
"""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from retrieval.hybrid_search import hybrid_search
from retrieval.reranker import rerank
from generation.prompt_builder import build_messages, extract_sources
from generation.llm import generate_stream
import structlog

router = APIRouter(tags=["stream"])
logger = structlog.get_logger()


@router.websocket("/api/ws/stream")
async def stream_query(ws: WebSocket):
    await ws.accept()
    logger.info("ws_connected")

    try:
        while True:
            raw = await ws.receive_text()
            req = json.loads(raw)
            question = req.get("question", "").strip()
            doc_filter = req.get("doc_filter")
            history = req.get("history", [])

            if not question:
                await ws.send_json({"type": "error", "data": "Empty question"})
                continue

            try:
                # Retrieve
                chunks = await hybrid_search(question, doc_filter=doc_filter)
                if not chunks:
                    await ws.send_json({"type": "error", "data": "No relevant documents found."})
                    continue

                # Rerank
                top_chunks = await rerank(question, chunks)

                # Send sources first
                sources = extract_sources(top_chunks)
                await ws.send_json({"type": "sources", "data": sources})

                # Build prompt
                system, messages = build_messages(question, top_chunks, history)

                # Stream tokens
                async for token in generate_stream(system, messages):
                    await ws.send_json({"type": "token", "data": token})

                await ws.send_json({"type": "done", "data": ""})

            except Exception as e:
                logger.error("ws_query_error", error=str(e))
                await ws.send_json({"type": "error", "data": str(e)})

    except WebSocketDisconnect:
        logger.info("ws_disconnected")
    except Exception as e:
        logger.error("ws_error", error=str(e))
