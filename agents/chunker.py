"""
agents/chunker.py
Node 4 – Chunking Layer
"""
from __future__ import annotations
import hashlib
import re

import tiktoken

from core.config import get_settings
from core.logging import get_logger
from core.models import DocumentChunk, PipelineState

logger = get_logger(__name__)

_ENCODER = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    return len(_ENCODER.encode(text))


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if not text.strip():
        return []

    paragraphs = re.split(r"\n{2,}|\.\s+", text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    chunks: list[str] = []
    current_tokens: list[int] = []
    current_text: list[str] = []

    for para in paragraphs:
        para_tokens = _ENCODER.encode(para)

        if len(current_tokens) + len(para_tokens) > chunk_size and current_tokens:
            chunks.append(" ".join(current_text))
            overlap_tokens = current_tokens[-overlap:] if overlap else []
            overlap_text = _ENCODER.decode(overlap_tokens) if overlap_tokens else ""
            current_tokens = list(overlap_tokens)
            current_text = [overlap_text] if overlap_text else []

        if len(para_tokens) > chunk_size:
            for i in range(0, len(para_tokens), chunk_size - overlap):
                sub = _ENCODER.decode(para_tokens[i : i + chunk_size])
                chunks.append(sub)
            current_tokens = []
            current_text = []
        else:
            current_tokens.extend(para_tokens)
            current_text.append(para)

    if current_text:
        chunks.append(" ".join(current_text))

    return chunks


def _build_chunk_id(url: str, index: int) -> str:
    base = f"{url}::{index}"
    return hashlib.sha1(base.encode()).hexdigest()[:12]


async def chunker_node(state: PipelineState) -> dict:
    """
    LangGraph node.
    Reads:  state['scraped_pages'], state['reranked_results']
    Writes: state['chunks']
    """
    settings = get_settings()
    chunk_size = settings.chunk_size_tokens
    overlap = settings.chunk_overlap_tokens

    scraped_pages = state.get("scraped_pages", {})
    reranked_results = state.get("reranked_results", [])

    title_map = {r.url: r.title for r in reranked_results}
    all_chunks: list[DocumentChunk] = []

    for url, text in scraped_pages.items():
        if not text.strip():
            continue

        title = title_map.get(url, "Unknown")
        raw_chunks = _chunk_text(text, chunk_size, overlap)

        for idx, chunk_text in enumerate(raw_chunks):
            all_chunks.append(
                DocumentChunk(
                    chunk_id=_build_chunk_id(url, idx),
                    source_url=url,
                    source_title=title,
                    text=chunk_text,
                    token_count=_count_tokens(chunk_text),
                )
            )

    logger.info("chunker_done", total_chunks=len(all_chunks))
    return {"chunks": all_chunks}
