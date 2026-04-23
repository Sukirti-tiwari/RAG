"""
LLM API integration.
Supports streaming and non-streaming generation across Anthropic, OpenAI, and Groq.
"""
from config import get_settings
import structlog

settings = get_settings()
logger = structlog.get_logger()

_anthropic_client = None
_openai_client = None
_groq_client = None


def get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import AsyncAnthropic
        _anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _anthropic_client

def get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import AsyncOpenAI
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client

def get_groq_client():
    global _groq_client
    if _groq_client is None:
        import groq
        _groq_client = groq.AsyncGroq(api_key=settings.groq_api_key)
    return _groq_client

async def generate(
    system: str,
    messages: list[dict],
    max_tokens: int | None = None,
) -> str:
    """Non-streaming generation. Returns complete answer string."""
    model = settings.llm_model
    max_tokens = max_tokens or settings.llm_max_tokens

    try:
        if "claude" in model.lower():
            client = get_anthropic_client()
            resp = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
            )
            logger.info(
                "llm_generated",
                input_tokens=resp.usage.input_tokens,
                output_tokens=resp.usage.output_tokens,
            )
            return resp.content[0].text
            
        elif "gpt" in model.lower():
            client = get_openai_client()
            combined_messages = [{"role": "system", "content": system}] + messages
            resp = await client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=combined_messages,
            )
            logger.info(
                "llm_generated",
                input_tokens=resp.usage.prompt_tokens,
                output_tokens=resp.usage.completion_tokens,
            )
            return resp.choices[0].message.content
            
        else:
            client = get_groq_client()
            combined_messages = [{"role": "system", "content": system}] + messages
            resp = await client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=combined_messages,
            )
            logger.info(
                "llm_generated",
                input_tokens=resp.usage.prompt_tokens,
                output_tokens=resp.usage.completion_tokens,
            )
            return resp.choices[0].message.content
    except Exception as e:
        logger.error("llm_error", error=str(e))
        return "Sorry, I encountered an error while generating the response. Please check your API keys or model configuration."


async def generate_stream(
    system: str,
    messages: list[dict],
    max_tokens: int | None = None,
):
    """Streaming generation. Yields text chunks as they arrive."""
    model = settings.llm_model
    max_tokens = max_tokens or settings.llm_max_tokens

    try:
        if "claude" in model.lower():
            client = get_anthropic_client()
            async with client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
                    
        elif "gpt" in model.lower():
            client = get_openai_client()
            combined_messages = [{"role": "system", "content": system}] + messages
            stream = await client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=combined_messages,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        else:
            client = get_groq_client()
            combined_messages = [{"role": "system", "content": system}] + messages
            stream = await client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=combined_messages,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
    except Exception as e:
        logger.error("llm_stream_error", error=str(e))
        yield " [Streaming error occurred. Check API keys and model configuration.]"
