"""
Groq API integration.
Supports both streaming (for WebSocket) and non-streaming (for REST).
"""
import groq
from config import get_settings
import structlog

settings = get_settings()
logger = structlog.get_logger()

_client: groq.AsyncGroq | None = None


def get_client() -> groq.AsyncGroq:
    global _client
    if _client is None:
        _client = groq.AsyncGroq(api_key=settings.groq_api_key)
    return _client


async def generate(
    system: str,
    messages: list[dict],
    max_tokens: int | None = None,
) -> str:
    """Non-streaming generation. Returns complete answer string."""
    client = get_client()
    
    # Combine system message into messages array for Groq
    groq_messages = [{"role": "system", "content": system}] + messages
    
    resp = await client.chat.completions.create(
        model=settings.llm_model,
        max_tokens=max_tokens or settings.llm_max_tokens,
        messages=groq_messages,
    )
    answer = resp.choices[0].message.content
    logger.info(
        "llm_generated",
        input_tokens=resp.usage.prompt_tokens,
        output_tokens=resp.usage.completion_tokens,
    )
    return answer


async def generate_stream(
    system: str,
    messages: list[dict],
    max_tokens: int | None = None,
):
    """
    Streaming generation. Yields text chunks as they arrive.
    Usage:
        async for chunk in generate_stream(system, messages):
            yield chunk
    """
    client = get_client()
    
    # Combine system message into messages array for Groq
    groq_messages = [{"role": "system", "content": system}] + messages
    
    stream = await client.chat.completions.create(
        model=settings.llm_model,
        max_tokens=max_tokens or settings.llm_max_tokens,
        messages=groq_messages,
        stream=True,
    )
    
    async for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
