"""
agents/reranker.py
Node 2 – Re-Ranker
"""
from __future__ import annotations
import asyncio
from functools import lru_cache

from sentence_transformers import CrossEncoder

from core.config import get_settings
from core.logging import get_logger
from core.models import PipelineState, SearchResult

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _get_cross_encoder() -> CrossEncoder:
    settings = get_settings()
    logger.info("loading_cross_encoder", model=settings.reranker_model)
    return CrossEncoder(settings.reranker_model)


def _rerank_sync(
    query: str,
    results: list[SearchResult],
    top_k: int,
) -> list[SearchResult]:
    if not results:
        return []

    model = _get_cross_encoder()
    pairs = [(query, f"{r.title}. {r.snippet}") for r in results]
    scores: list[float] = model.predict(pairs).tolist()

    for result, score in zip(results, scores):
        result.rerank_score = float(score)

    ranked = sorted(results, key=lambda r: r.rerank_score, reverse=True)
    return ranked[:top_k]


async def reranker_node(state: PipelineState) -> dict:
    """
    LangGraph node.
    Reads:  state['search_results'], state['query']
    Writes: state['reranked_results']
    """
    settings = get_settings()
    top_k = settings.reranker_top_k
    search_results = state.get("search_results", [])
    query = state.get("query", "")

    logger.info("reranker_start", total_results=len(search_results), keep_top_k=top_k)

    if not search_results:
        logger.warning("reranker_no_input")
        return {"reranked_results": []}

    loop = asyncio.get_event_loop()
    reranked = await loop.run_in_executor(
        None, _rerank_sync, query, list(search_results), top_k
    )

    logger.info(
        "reranker_done",
        kept=len(reranked),
        top_score=reranked[0].rerank_score if reranked else None,
    )
    return {"reranked_results": reranked}
