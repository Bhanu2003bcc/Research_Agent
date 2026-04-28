"""
agents/reader_agent.py
Node 3 – Reader Agent
Asynchronously scrapes each re-ranked URL and stores clean text in state.
Falls back to the Exa snippet text if scraping is blocked (HTTP 403 etc.)
"""
from __future__ import annotations

from core.logging import get_logger
from core.models import PipelineState
from tools.bs4_scraper import BS4Scraper

logger = get_logger(__name__)


async def reader_agent_node(state: PipelineState) -> dict:
    """
    LangGraph node.
    Reads:  state['reranked_results']
    Writes: state['scraped_pages']  (url -> clean text)
    """
    reranked_results = state.get("reranked_results", [])
    if not reranked_results:
        logger.warning("reader_agent_no_urls")
        return {"scraped_pages": {}}

    urls = [r.url for r in reranked_results]
    logger.info("reader_agent_start", url_count=len(urls))

    scraper = BS4Scraper()
    scraped = await scraper.scrape_urls(urls)

    # Build a snippet lookup from reranked results for fallback
    snippet_map = {r.url: r.snippet for r in reranked_results}

    # Merge: use scraped text if available, fall back to Exa snippet
    merged: dict[str, str] = {}
    for url in urls:
        text = scraped.get(url, "")
        if text.strip():
            merged[url] = text
        elif snippet_map.get(url, "").strip():
            logger.info("reader_agent_snippet_fallback", url=url)
            merged[url] = snippet_map[url]
        else:
            merged[url] = ""

    successful = sum(1 for v in merged.values() if v.strip())
    logger.info(
        "reader_agent_done",
        scraped=len(urls),
        with_content=successful,
    )

    return {"scraped_pages": merged}
