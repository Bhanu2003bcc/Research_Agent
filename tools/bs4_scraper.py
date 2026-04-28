"""
tools/bs4_scraper.py
Async web scraper using aiohttp + BeautifulSoup.
Removes boilerplate (nav, footer, ads, scripts, styles) and returns clean text.
"""
from __future__ import annotations
import asyncio
import re
from typing import Optional

import aiohttp
import chardet
from bs4 import BeautifulSoup, Comment
from tenacity import retry, stop_after_attempt, wait_fixed

from core.config import get_settings
from core.logging import get_logger

logger = get_logger(__name__)

_BOILERPLATE_TAGS = {
    "script", "style", "noscript", "header", "footer",
    "nav", "aside", "form", "button", "meta", "link",
    "iframe", "svg", "canvas", "advertisement", "ad",
}

_NOISY_CLASS_PATTERNS = re.compile(
    r"(nav|menu|sidebar|footer|header|banner|cookie|popup|modal|ad[-_]|ads[-_]|"
    r"social|share|related|comment|subscribe|newsletter|promo)",
    re.IGNORECASE,
)

_WHITESPACE_RE = re.compile(r"\s{3,}")


def _detect_encoding(raw: bytes) -> str:
    detection = chardet.detect(raw[:10_000])
    return detection.get("encoding") or "utf-8"


def _clean_html(html: str) -> str:
    """Strip boilerplate, return plain text."""
    soup = BeautifulSoup(html, "lxml")

    # Remove comment nodes
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    # Remove noisy structural tags
    for tag in soup.find_all(_BOILERPLATE_TAGS):
        tag.decompose()

    # Remove elements whose class/id suggests they're boilerplate
    for tag in soup.find_all(True):
        cls = " ".join(tag.get("class", []))
        tag_id = tag.get("id", "")
        if _NOISY_CLASS_PATTERNS.search(cls) or _NOISY_CLASS_PATTERNS.search(tag_id):
            tag.decompose()

    # Extract main content heuristic: prefer <article>, <main>, <section>
    main_content = (
        soup.find("article")
        or soup.find("main")
        or soup.find("div", {"id": re.compile(r"content|article|post", re.I)})
        or soup.find("div", {"class": re.compile(r"content|article|post", re.I)})
        or soup.body
    )

    if main_content is None:
        return ""

    text = main_content.get_text(separator="\n")
    text = _WHITESPACE_RE.sub("\n\n", text)
    return text.strip()


class BS4Scraper:
    """
    Async URL scraper with concurrency control, timeout, and graceful failure.
    """

    def __init__(
        self,
        timeout_seconds: Optional[int] = None,
        max_concurrent: Optional[int] = None,
    ):
        settings = get_settings()
        self._timeout = aiohttp.ClientTimeout(
            total=timeout_seconds or settings.reader_timeout_seconds
        )
        self._semaphore = asyncio.Semaphore(
            max_concurrent or settings.reader_max_concurrent
        )
        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }

    @retry(stop=stop_after_attempt(2), wait=wait_fixed(1), reraise=False)
    async def _fetch_one(
        self, session: aiohttp.ClientSession, url: str
    ) -> tuple[str, str]:
        """
        Returns (url, clean_text). Returns empty string on any failure.
        """
        async with self._semaphore:
            try:
                async with session.get(
                    url,
                    headers=self._headers,
                    timeout=self._timeout,
                    allow_redirects=True,
                    ssl=False,
                ) as resp:
                    if resp.status in (403, 429, 451):
                        logger.warning(
                            "scraper_blocked", url=url, status=resp.status
                        )
                        # Try without the full header set (some sites block Sec-Fetch)
                        return url, ""
                    if resp.status == 404 or resp.status == 410:
                        return url, ""
                    if resp.status != 200:
                        logger.warning(
                            "scraper_non_200", url=url, status=resp.status
                        )
                        return url, ""

                    raw = await resp.read()
                    encoding = _detect_encoding(raw)
                    html = raw.decode(encoding, errors="replace")
                    text = _clean_html(html)
                    logger.info(
                        "scraper_success",
                        url=url,
                        chars=len(text),
                    )
                    return url, text
            except asyncio.TimeoutError:
                logger.warning("scraper_timeout", url=url)
                return url, ""
            except Exception as exc:
                logger.warning("scraper_error", url=url, error=str(exc))
                return url, ""

    async def scrape_urls(self, urls: list[str]) -> dict[str, str]:
        """
        Scrape multiple URLs concurrently.
        Returns dict: url -> clean_text (empty string if failed).
        """
        connector = aiohttp.TCPConnector(limit=0, force_close=True)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [self._fetch_one(session, url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        output: dict[str, str] = {}
        for item in results:
            if isinstance(item, Exception):
                logger.error("scraper_gather_exception", error=str(item))
                continue
            url, text = item
            output[url] = text

        logger.info(
            "scraper_batch_done",
            total=len(urls),
            successful=sum(1 for v in output.values() if v),
        )
        return output
