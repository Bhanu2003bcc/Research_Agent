"""
agents/embedder.py
Node 5 – Embedding + Indexing
"""
from __future__ import annotations
import asyncio
import pickle
from functools import lru_cache

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from core.config import get_settings
from core.logging import get_logger
from core.models import DocumentChunk, PipelineState

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _get_encoder() -> SentenceTransformer:
    settings = get_settings()
    logger.info("loading_embedding_model", model=settings.embedding_model)
    return SentenceTransformer(settings.embedding_model)


def _embed_and_index(chunks: list[DocumentChunk]) -> tuple[bytes, list[DocumentChunk]]:
    encoder = _get_encoder()
    texts = [c.text for c in chunks]

    logger.info("embedding_start", count=len(texts))
    embeddings: np.ndarray = encoder.encode(
        texts,
        batch_size=64,
        show_progress_bar=False,
        normalize_embeddings=True,
    )

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings.astype(np.float32))

    for chunk, emb in zip(chunks, embeddings):
        chunk.embedding = emb.tolist()

    index_bytes = pickle.dumps(index)
    logger.info("indexing_done", dim=dim, vectors=index.ntotal)
    return index_bytes, chunks


async def embedder_node(state: PipelineState) -> dict:
    """
    LangGraph node.
    Reads:  state['chunks']
    Writes: state['faiss_index_bytes'], state['chunks'] (with embeddings)
    """
    chunks = state.get("chunks", [])
    if not chunks:
        logger.warning("embedder_no_chunks")
        return {"faiss_index_bytes": None}

    loop = asyncio.get_event_loop()
    index_bytes, enriched_chunks = await loop.run_in_executor(
        None, _embed_and_index, chunks
    )

    return {
        "faiss_index_bytes": index_bytes,
        "chunks": enriched_chunks,
    }
