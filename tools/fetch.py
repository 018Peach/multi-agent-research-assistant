"""`fetch_page` tool — turn a URL into clean markdown via Firecrawl so the Critic
can open and verify a cited source, not just trust a snippet (spec §7.2, ADR-004).

Returns `as_untrusted`-fenced markdown (truncated). Failures return a short error
string the agent can reason about — never an exception that kills the branch.
"""

from __future__ import annotations

import logging

from langchain_core.tools import tool

from config import get_settings
from tools.untrusted import as_untrusted

logger = logging.getLogger("tools.fetch")

_MAX_CHARS = 8000
_client = None


def _get_client():
    global _client
    if _client is None:
        from firecrawl import Firecrawl

        _client = Firecrawl(api_key=get_settings().firecrawl_api_key)
    return _client


def _truncate(text: str, n: int = _MAX_CHARS) -> str:
    return text if len(text) <= n else text[:n] + "\n\n…[truncated]"


@tool
def fetch_page(url: str) -> str:
    """Fetch `url` as clean markdown (Firecrawl) for source verification."""
    s = get_settings()
    if not s.firecrawl_api_key:
        return f"fetch_page unavailable: no Firecrawl API key configured (url={url})."
    try:
        doc = _get_client().scrape(
            url,
            formats=["markdown"],
            only_main_content=True,
            timeout=s.request_timeout * 1000,   # Firecrawl timeout is milliseconds
        )
        markdown = getattr(doc, "markdown", None) or ""
        if not markdown.strip():
            return f"fetch_page: no readable content returned for {url}."
        return as_untrusted(_truncate(markdown))
    except Exception as e:  # noqa: BLE001 - return a short error, don't kill the branch
        logger.warning("fetch_page failed for %s: %s", url, type(e).__name__)
        return f"fetch_page error for {url}: {type(e).__name__}: {e}"
