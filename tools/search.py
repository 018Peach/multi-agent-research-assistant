"""`web_search` tool — ordered provider fallback Tavily → Exa → Gemini Google
Search, each normalised to `SearchResult` (spec §7.1, ADR-004).

External providers (Tavily/Exa) fire as visible tool calls and are skipped if their
key is unset; Gemini's built-in Google Search is the keyless last resort (reuses
the Gemini key). The tool returns an `as_untrusted`-fenced string (§7.4) so the
agent reads results as data, not instructions.
"""

from __future__ import annotations

import logging

from langchain_core.tools import tool

from config import get_settings
from schemas import SearchResult
from tools.untrusted import as_untrusted

logger = logging.getLogger("tools.search")

_MAX_RESULTS = 5
_SNIPPET_CHARS = 500


def _clip(text: str | None, n: int = _SNIPPET_CHARS) -> str:
    text = (text or "").strip().replace("\n", " ")
    return text if len(text) <= n else text[:n] + "…"


# ───────────────────────────── providers ────────────────────────────────────
class TavilyProvider:
    """Primary provider (spec §7.1)."""

    name = "tavily"

    def __init__(self) -> None:
        self._client = None

    def available(self) -> bool:
        return bool(get_settings().tavily_api_key)

    def _get_client(self):
        if self._client is None:
            from tavily import TavilyClient

            self._client = TavilyClient(api_key=get_settings().tavily_api_key)
        return self._client

    def search(self, query: str) -> list[SearchResult]:
        resp = self._get_client().search(
            query, max_results=_MAX_RESULTS, timeout=get_settings().request_timeout
        )
        return [
            SearchResult(
                title=r.get("title") or r.get("url", ""),
                url=r.get("url", ""),
                snippet=_clip(r.get("content")),
                provider="tavily",
            )
            for r in (resp.get("results") or [])
            if r.get("url")
        ]


class ExaProvider:
    """Secondary provider (spec §7.1)."""

    name = "exa"

    def __init__(self) -> None:
        self._client = None

    def available(self) -> bool:
        return bool(get_settings().exa_api_key)

    def _get_client(self):
        if self._client is None:
            from exa_py import Exa

            self._client = Exa(api_key=get_settings().exa_api_key)
        return self._client

    def search(self, query: str) -> list[SearchResult]:
        resp = self._get_client().search(query, num_results=_MAX_RESULTS)
        out: list[SearchResult] = []
        for r in getattr(resp, "results", []) or []:
            url = getattr(r, "url", None)
            if not url:
                continue
            highlights = getattr(r, "highlights", None) or []
            snippet = highlights[0] if highlights else (getattr(r, "text", None) or getattr(r, "summary", None))
            out.append(
                SearchResult(
                    title=getattr(r, "title", None) or url,
                    url=url,
                    snippet=_clip(snippet),
                    provider="exa",
                )
            )
        return out


class GeminiGroundingProvider:
    """Keyless last resort — Gemini's built-in Google Search (ADR-004). Reuses the
    Gemini key pool; maps `groundingChunks` → `SearchResult(provider="gemini")`."""

    name = "gemini"

    def available(self) -> bool:
        return True  # always available (uses the Gemini key)

    def search(self, query: str) -> list[SearchResult]:
        from google import genai
        from google.genai import types

        from llm.keys import get_pool

        s = get_settings()
        client = genai.Client(api_key=get_pool().current())
        resp = client.models.generate_content(
            model=s.model_name,
            contents=query,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        candidates = getattr(resp, "candidates", None) or []
        if not candidates:
            return []
        meta = getattr(candidates[0], "grounding_metadata", None)
        chunks = getattr(meta, "grounding_chunks", None) or []
        out: list[SearchResult] = []
        for ch in chunks[:_MAX_RESULTS]:
            web = getattr(ch, "web", None)
            if web is None or not getattr(web, "uri", None):
                continue
            out.append(
                SearchResult(
                    title=getattr(web, "title", None) or web.uri,
                    url=web.uri,
                    snippet=_clip(getattr(resp, "text", None)),
                    provider="gemini",
                )
            )
        return out


_PROVIDERS: dict[str, object] = {
    "tavily": TavilyProvider(),
    "exa": ExaProvider(),
    "gemini": GeminiGroundingProvider(),
}


def _format_results(results: list[SearchResult], query: str) -> str:
    if not results:
        return f"No search results found for: {query}"
    lines = [f"Search results for: {query}"]
    for i, r in enumerate(results, 1):
        lines.append(f"\n[{i}] {r.title}\nURL: {r.url}\nSnippet: {r.snippet}")
    return "\n".join(lines)


@tool
def web_search(query: str) -> str:
    """Search the web for `query`. Tries Tavily, then Exa, then Gemini Google
    Search, returning the first provider's normalised results (title, url, snippet)
    as untrusted data."""
    results: list[SearchResult] = []
    used: str | None = None
    for name in get_settings().providers:
        provider = _PROVIDERS.get(name)
        if provider is None or not provider.available():  # type: ignore[attr-defined]
            continue
        try:
            results = provider.search(query)  # type: ignore[attr-defined]
        except Exception as e:  # noqa: BLE001 - defensive: try the next provider
            logger.warning("search provider '%s' failed: %s", name, type(e).__name__)
            continue
        if results:
            used = name
            break
    if used:
        logger.info("web_search: %d result(s) via %s", len(results), used)
    return as_untrusted(_format_results(results, query))
