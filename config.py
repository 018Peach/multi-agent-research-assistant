"""Configuration — single source of truth for behavioural knobs (spec §2, §14).

One `Settings` object loaded once from `.env` via `pydantic-settings`. Import the
cached `get_settings()` singleton in nodes, tools, and routing rather than reading
`os.getenv` or threading `Settings` through every signature (spec §0, §2).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application config, populated from `.env` (ADR-018)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Gemini ────────────────────────────────────────────────────────────
    gemini_api_keys: str                       # comma-separated free-tier keys
    model_name: str = "gemini-3-flash-preview"
    max_output_tokens: int = 8192

    # ── Search / fetch ────────────────────────────────────────────────────
    tavily_api_key: str | None = None
    exa_api_key: str | None = None
    firecrawl_api_key: str | None = None
    search_provider_order: str = "tavily,exa,gemini"

    # ── Behaviour / guardrails ────────────────────────────────────────────
    max_subtasks: int = 3
    max_research_iterations: int = 1            # retries (not passes)
    confidence_threshold: float = 0.7

    # ── Per-agent bounds (reset per invocation — §4, ADR-019) ─────────────
    plan_max_steps: int = 4
    plan_max_tool_calls: int = 8
    research_max_steps: int = 5
    research_max_tool_calls: int = 10
    critic_max_steps: int = 10
    critic_max_tool_calls: int = 30
    recursion_limit: int = 50                   # graph-level backstop

    # ── Infra ─────────────────────────────────────────────────────────────
    request_timeout: int = 60
    db_path: str = "./.runtime/checkpoints.sqlite"   # runtime artifacts kept under .runtime/
    compaction_token_threshold: int = 160_000   # deferred (unused)
    price_input_per_m: float | None = None
    price_output_per_m: float | None = None

    # ── Derived helpers ───────────────────────────────────────────────────
    @property
    def gemini_keys(self) -> list[str]:
        """The Gemini key pool, parsed from the comma-separated env value."""
        return [k.strip() for k in self.gemini_api_keys.split(",") if k.strip()]

    @property
    def providers(self) -> list[str]:
        """Ordered search providers (e.g. ``["tavily", "exa", "gemini"]``)."""
        return [p.strip() for p in self.search_provider_order.split(",") if p.strip()]


# Per-node thinking tiers (Gemini 3 `thinking_level`) — spec §2/§6, ADR-018.
THINKING: dict[str, str] = {
    "plan": "high",
    "critic": "high",
    "write": "high",
    "research": "medium",
}


def agent_bounds(s: Settings, node: str) -> tuple[int, int]:
    """Return ``(max_steps, max_tool_calls)`` for an agentic node (spec §2, §5)."""
    return {
        "plan": (s.plan_max_steps, s.plan_max_tool_calls),
        "research": (s.research_max_steps, s.research_max_tool_calls),
        "critic": (s.critic_max_steps, s.critic_max_tool_calls),
        "write": (1, 0),
    }[node]


@lru_cache
def get_settings() -> Settings:
    """Cached `Settings` singleton (loaded once from `.env`)."""
    return Settings()  # type: ignore[call-arg]  # fields populated from env
