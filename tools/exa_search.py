"""
tools/exa_search.py
Exa API integration – real-time web search with live results.
"""
from __future__ import annotations
import asyncio
from typing import Optional

from exa_py import Exa
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from core.config import get_settings
from core.models import SearchResult
from core.logging import get_logger

logger = get_logger(__name__)


class ExaSearchTool:
    """
    Wraps the Exa Python SDK to return SearchResult objects.
    Uses the highlights endpoint for rich snippets.
    """

    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self._client = Exa(api_key=api_key or settings.exa_api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def _search_sync(self, query: str, num_results: int) -> list[SearchResult]:
        """Synchronous Exa search with highlights."""
        logger.info("exa_search_start", query=query, num_results=num_results)

        response = self._client.search_and_contents(
            query,
            num_results=num_results,
            highlights={
                "num_sentences": 3,
                "highlights_per_url": 1,
            },
            text=False,  # we scrape full text ourselves via Reader Agent
        )

        results: list[SearchResult] = []
        for r in response.results:
            snippet = ""
            if hasattr(r, "highlights") and r.highlights:
                snippet = " … ".join(r.highlights)
            elif hasattr(r, "text") and r.text:
                snippet = r.text[:300]

            results.append(
                SearchResult(
                    title=r.title or "Untitled",
                    url=r.url,
                    snippet=snippet,
                    score=float(getattr(r, "score", 0.0) or 0.0),
                )
            )

        logger.info("exa_search_complete", count=len(results))
        return results

    async def search(self, query: str, num_results: int = 10) -> list[SearchResult]:
        """Async-friendly wrapper — runs sync call in a thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._search_sync, query, num_results
        )
