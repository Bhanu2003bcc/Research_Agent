"""
core/pipeline.py
LangGraph state machine – wires every agent node into the full pipeline.
"""
from __future__ import annotations
from typing import Literal

from langgraph.graph import StateGraph, END

from agents.chunker import chunker_node
from agents.critic_agent import critic_agent_node
from agents.embedder import embedder_node
from agents.finalizer import finalizer_node
from agents.reader_agent import reader_agent_node
from agents.reranker import reranker_node
from agents.retriever import retriever_node
from agents.search_agent import search_agent_node
from agents.writer_agent import writer_agent_node
from core.config import get_settings
from core.logging import get_logger
from core.models import PipelineState

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Conditional edge: should we run another refinement iteration?
# ---------------------------------------------------------------------------

def _should_refine(state: PipelineState) -> Literal["refine", "finalise"]:
    settings = get_settings()
    max_iter = settings.refinement_max_iterations
    iteration = state.get("refinement_iteration", 0)
    critic_feedback = state.get("critic_feedback")

    if iteration >= max_iter:
        logger.info("refinement_complete", iterations=iteration)
        return "finalise"

    if critic_feedback and critic_feedback.overall_quality >= 0.88:
        logger.info("refinement_skipped_high_quality", quality=critic_feedback.overall_quality)
        return "finalise"

    logger.info("refinement_continue", iteration=iteration + 1)
    return "refine"


# ---------------------------------------------------------------------------
# Increment refinement counter helper node
# ---------------------------------------------------------------------------

async def _increment_iteration(state: PipelineState) -> dict:
    return {"refinement_iteration": state.get("refinement_iteration", 0) + 1}


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_pipeline() -> StateGraph:
    graph = StateGraph(PipelineState)

    graph.add_node("search", search_agent_node)
    graph.add_node("rerank", reranker_node)
    graph.add_node("read", reader_agent_node)
    graph.add_node("chunk", chunker_node)
    graph.add_node("embed", embedder_node)
    graph.add_node("retrieve", retriever_node)
    graph.add_node("write", writer_agent_node)
    graph.add_node("critique", critic_agent_node)
    graph.add_node("increment_iter", _increment_iteration)
    graph.add_node("finalise", finalizer_node)

    graph.set_entry_point("search")
    graph.add_edge("search", "rerank")
    graph.add_edge("rerank", "read")
    graph.add_edge("read", "chunk")
    graph.add_edge("chunk", "embed")
    graph.add_edge("embed", "retrieve")
    graph.add_edge("retrieve", "write")
    graph.add_edge("write", "critique")

    graph.add_conditional_edges(
        "critique",
        _should_refine,
        {
            "refine": "increment_iter",
            "finalise": "finalise",
        },
    )

    graph.add_edge("increment_iter", "write")
    graph.add_edge("finalise", END)

    return graph


def compile_pipeline():
    """Return a compiled, runnable LangGraph pipeline."""
    graph = build_pipeline()
    return graph.compile()
