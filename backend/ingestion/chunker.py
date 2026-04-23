"""
Recursive character text splitter.
Splits on paragraphs → sentences → words, respecting chunk_size and overlap.
"""
import re
import tiktoken
from config import get_settings

settings = get_settings()
_enc = tiktoken.encoding_for_model("text-embedding-3-small")


def count_tokens(text: str) -> int:
    return len(_enc.encode(text))


def split_text(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[str]:
    size = chunk_size or settings.chunk_size
    overlap = chunk_overlap or settings.chunk_overlap

    separators = ["\n\n", "\n", ". ", "! ", "? ", ", ", " ", ""]

    def _split(text: str, separators: list[str]) -> list[str]:
        sep = separators[0]
        remaining = separators[1:]

        if sep:
            splits = re.split(re.escape(sep), text)
        else:
            splits = list(text)

        chunks = []
        current_tokens = 0
        current_parts = []

        for part in splits:
            part_tokens = count_tokens(part)
            if part_tokens > size and remaining:
                if current_parts:
                    chunks.append(sep.join(current_parts))
                    current_parts = []
                    current_tokens = 0
                chunks.extend(_split(part, remaining))
                continue

            if current_tokens + part_tokens > size and current_parts:
                chunks.append(sep.join(current_parts))
                # Keep last overlap tokens
                overlap_parts = []
                overlap_tokens = 0
                for p in reversed(current_parts):
                    t = count_tokens(p)
                    if overlap_tokens + t > overlap:
                        break
                    overlap_parts.insert(0, p)
                    overlap_tokens += t
                current_parts = overlap_parts
                current_tokens = overlap_tokens

            current_parts.append(part)
            current_tokens += part_tokens

        if current_parts:
            chunks.append(sep.join(current_parts))

        return [c.strip() for c in chunks if c.strip()]

    return _split(text, separators)


def chunk_pages(
    pages: list[dict],
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[dict]:
    """
    Takes loader output (list of page dicts) and returns
    flat list of chunk dicts with inherited metadata.
    """
    all_chunks = []
    chunk_idx = 0

    for page in pages:
        content = page.get("content", "").strip()
        if not content:
            continue

        texts = split_text(content, chunk_size, chunk_overlap)
        for text in texts:
            all_chunks.append({
                "content": text,
                "chunk_index": chunk_idx,
                "page": page.get("page"),
                "token_count": count_tokens(text),
                "metadata": page.get("metadata", {}),
            })
            chunk_idx += 1

    return all_chunks
