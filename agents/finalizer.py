"""
agents/finalizer.py
Terminal Node – builds the structured ResearchResponse from pipeline state.
"""
from __future__ import annotations
import re

from core.logging import get_logger
from core.models import CriticFeedback, PipelineState

logger = get_logger(__name__)

_URL_RE = re.compile(r"https?://[^\s\]>\"']+")


def _extract_cited_urls(answer: str) -> list[str]:
    """Pull every URL mentioned inside [Source: ...] citations."""
    return list(dict.fromkeys(_URL_RE.findall(answer)))


def _compute_confidence(critic_feedback, retrieved_chunks: list) -> float:
    if critic_feedback:
        cf = critic_feedback
        confidence = (
            0.35 * cf.factual_correctness_score
            + 0.30 * cf.completeness_score
            + 0.20 * (1 - cf.hallucination_risk)
            + 0.15 * cf.overall_quality
        )
    else:
        retrieved = len(retrieved_chunks)
        confidence = min(0.5 + retrieved * 0.03, 0.75)

    return round(float(confidence), 3)


async def finalizer_node(state: PipelineState) -> dict:
    """
    LangGraph node.
    Reads:  state['draft_answer'], state['retrieved_chunks'], state['reranked_results']
    Writes: state['final_answer'], state['sources'], state['confidence']
    """
    final_answer = state.get("draft_answer") or "No answer could be generated."

    cited = _extract_cited_urls(final_answer)
    reranked_results = state.get("reranked_results", [])
    search_urls = [r.url for r in reranked_results]
    all_sources = list(dict.fromkeys(cited + search_urls))

    retrieved_chunks = state.get("retrieved_chunks", [])
    critic_feedback = state.get("critic_feedback")
    confidence = _compute_confidence(critic_feedback, retrieved_chunks)

    logger.info(
        "finalizer_done",
        answer_length=len(final_answer),
        sources=len(all_sources),
        confidence=confidence,
    )

    return {
        "final_answer": final_answer,
        "sources": all_sources,
        "confidence": confidence,
    }
