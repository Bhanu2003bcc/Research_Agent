"""
agents/search_agent.py
Node 1 – Search Agent
Uses Exa API to fetch the top-N real-time web results for the research query.
"""
from __future__ import annotations

from core.config import get_settings
from core.logging import get_logger
from core.models import PipelineState
from tools.exa_search import ExaSearchTool

logger = get_logger(__name__)


async def search_agent_node(state: PipelineState) -> dict:
    """
    LangGraph node.
    Reads:  state['query']
    Writes: state['search_results']
    """
    settings = get_settings()
    top_n = settings.search_top_n

    query = state.get("query", "")
    logger.info("search_agent_start", query=query, top_n=top_n)

    tool = ExaSearchTool()
    try:
        results = await tool.search(query, num_results=top_n)
    except Exception as exc:
        logger.error("search_agent_failed", error=str(exc))
        errors = list(state.get("errors", []))
        errors.append(f"SearchAgent: {exc}")
        return {"errors": errors}

    logger.info("search_agent_done", results_count=len(results))
    return {"search_results": results}
