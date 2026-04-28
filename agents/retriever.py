"""
agents/retriever.py
Node 6 – Retriever
"""
from __future__ import annotations
import asyncio
import pickle

import faiss
import numpy as np

from agents.embedder import _get_encoder
from core.config import get_settings
from core.logging import get_logger
from core.models import DocumentChunk, PipelineState

logger = get_logger(__name__)


def _retrieve_sync(
    query: str,
    index_bytes: bytes,
    chunks: list[DocumentChunk],
    top_k: int,
) -> list[DocumentChunk]:
    encoder = _get_encoder()
    index: faiss.IndexFlatIP = pickle.loads(index_bytes)

    query_vec: np.ndarray = encoder.encode(
        [query], normalize_embeddings=True
    ).astype(np.float32)

    k = min(top_k, index.ntotal)
    distances, indices = index.search(query_vec, k)

    retrieved: list[DocumentChunk] = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0:
            continue
        chunk = chunks[idx]
        logger.debug(
            "retrieved_chunk",
            chunk_id=chunk.chunk_id,
            score=float(dist),
            url=chunk.source_url,
        )
        retrieved.append(chunk)

    return retrieved


async def retriever_node(state: PipelineState) -> dict:
    """
    LangGraph node.
    Reads:  state['query'], state['faiss_index_bytes'], state['chunks']
    Writes: state['retrieved_chunks']
    """
    settings = get_settings()
    top_k = settings.retriever_top_k

    index_bytes = state.get("faiss_index_bytes")
    chunks = state.get("chunks", [])

    if not index_bytes or not chunks:
        logger.warning("retriever_no_index")
        return {"retrieved_chunks": []}

    loop = asyncio.get_event_loop()
    retrieved = await loop.run_in_executor(
        None,
        _retrieve_sync,
        state.get("query", ""),
        index_bytes,
        chunks,
        top_k,
    )

    logger.info("retriever_done", retrieved_chunks=len(retrieved))
    return {"retrieved_chunks": retrieved}
