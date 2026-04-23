"""
Prompt builder: assembles retrieved chunks into a structured prompt
with numbered citations that the LLM can reference in its answer.
"""
from config import get_settings

settings = get_settings()

SYSTEM_PROMPT = """You are a precise and helpful AI assistant that answers questions based on the provided context documents.

Rules:
1. Base your answers ONLY on the provided context. Do not use outside knowledge unless explicitly asked.
2. Cite your sources using [1], [2], etc. when making a factual claim.
3. If the context does not contain enough information to answer confidently, say so clearly.
4. Be concise but thorough. Use bullet points or numbered lists when appropriate.
5. If multiple sources agree, synthesize them. If they conflict, note the discrepancy.
6. Never fabricate citations or facts not present in the context."""


def build_context_block(chunks: list[dict]) -> str:
    """Format retrieved chunks as a numbered citation block."""
    lines = []
    for i, chunk in enumerate(chunks, 1):
        page_info = f" (page {chunk['page']})" if chunk.get("page") else ""
        lines.append(f"[{i}]{page_info}:\n{chunk['content']}")
    return "\n\n".join(lines)


def build_messages(
    question: str,
    chunks: list[dict],
    history: list[dict] | None = None,
) -> tuple[str, list[dict]]:
    """
    Returns (system_prompt, messages) ready for the Anthropic API.
    history: list of {"role": "user"|"assistant", "content": str}
    """
    context = build_context_block(chunks)

    user_content = f"""Context documents:
---
{context}
---

Question: {question}

Answer based on the context above. Include citation numbers like [1], [2] in your response."""

    messages = []
    if history:
        for turn in history[-6:]:  # keep last 3 exchanges
            messages.append({"role": turn["role"], "content": turn["content"]})

    messages.append({"role": "user", "content": user_content})
    return SYSTEM_PROMPT, messages


def extract_sources(chunks: list[dict]) -> list[dict]:
    """Build source metadata list for the frontend."""
    return [
        {
            "citation": i + 1,
            "content": chunk["content"][:300] + ("..." if len(chunk["content"]) > 300 else ""),
            "doc_id": chunk.get("doc_id", ""),
            "page": chunk.get("page"),
            "chunk_index": chunk.get("chunk_index", 0),
            "score": round(chunk.get("rerank_score", chunk.get("score", 0)), 4),
        }
        for i, chunk in enumerate(chunks)
    ]
