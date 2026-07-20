"""LLM factory + call wrapper with the error-classification policy (spec §6.2,
ADR-003).

`get_llm(node)` returns a `ChatGoogleGenerativeAI` configured for the node (model,
per-node `thinking_level`, output cap, timeout, current key). Every LLM/agent call
is wrapped by `call_with_rotation`, which classifies failures and acts: rotate on
rate limits, cool on daily-quota exhaustion, drop on auth errors, back off on
transient errors, surface bad requests, and raise `AllKeysExhausted` when the pool
is empty (→ graceful degradation, §10).

Security: we log the key **index**, never the key (spec §6).
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Awaitable, Callable, TypeVar

from langchain_google_genai import ChatGoogleGenerativeAI

from config import THINKING, get_settings
from llm.keys import AllKeysExhausted, KeyPool, get_pool

logger = logging.getLogger("llm.client")

T = TypeVar("T")

# Failure categories (ADR-003).
RATE = "rate"            # 429, transient rate limit  -> rotate
QUOTA_DAILY = "quota_daily"  # 429, daily free-tier cap -> cool + rotate
AUTH = "auth"            # 401/403 invalid key        -> drop + rotate
TRANSIENT = "transient"  # 5xx / timeout / network    -> backoff (+ rotate if persists)
FATAL = "fatal"          # 400 / safety / bad request -> raise (not a key problem)

# Tunables.
_DAILY_COOL_SECS = 3600.0      # skip a daily-exhausted key for the rest of a session
_RATE_COOL_SECS = 30.0         # brief skip for a rate-limited key (used if no server hint)
_BACKOFF_BASE = 0.5
_BACKOFF_CAP = 8.0
_TRANSIENT_RETRIES_BEFORE_ROTATE = 2


# ───────────────────────────── client factory ───────────────────────────────
def get_llm(
    node: str,
    *,
    structured: type | None = None,
    tools: list | None = None,
) -> Any:
    """Return a `ChatGoogleGenerativeAI` configured for `node` using the current key.

    `thinking_level` comes from `THINKING[node]`. `max_retries=1` disables the
    Google SDK's own 429 retry so our `call_with_rotation` governs rotation
    (the SDK otherwise backs off internally and ignores the pool). Built per
    invocation so key rotation can rebuild it (spec §5/§6).
    """
    s = get_settings()
    llm = ChatGoogleGenerativeAI(
        model=s.model_name,
        google_api_key=get_pool().current(),
        thinking_level=THINKING[node],          # "high" | "medium" (P0-verified)
        max_output_tokens=s.max_output_tokens,
        timeout=s.request_timeout,
        max_retries=1,                          # our rotation owns retries (§6)
        include_thoughts=True,                  # thought summaries for the §9 pane (P0)
    )
    if structured is not None:
        llm = llm.with_structured_output(structured)
    if tools:
        llm = llm.bind_tools(tools)
    return llm


# ───────────────────────────── error classification ─────────────────────────
def _status_code(exc: BaseException) -> int | None:
    """Best-effort HTTP status code from a Gemini/transport exception."""
    for attr in ("code", "status_code"):
        val = getattr(exc, attr, None)
        if isinstance(val, int):
            return val
    resp = getattr(exc, "response", None)
    code = getattr(resp, "status_code", None)
    if isinstance(code, int):
        return code
    m = re.search(r"\b(4\d\d|5\d\d)\b", str(exc))
    return int(m.group(1)) if m else None


def _is_timeout_or_network(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError, ConnectionError)):
        return True
    name = type(exc).__name__.lower()
    if "timeout" in name or "connect" in name or "transport" in name:
        return True
    text = str(exc).lower()
    return "timeout" in text or "deadline" in text or "connection" in text


def classify_error(exc: BaseException) -> str:
    """Map an exception to a failure category (ADR-003)."""
    text = str(exc).lower()
    code = _status_code(exc)

    if code == 429 or "resource_exhausted" in text or "too many requests" in text:
        # daily free-tier cap vs. a transient per-minute rate limit
        if any(t in text for t in ("perday", "per day", "per-day", "requests_per_day", "daily")):
            return QUOTA_DAILY
        return RATE

    if code in (401, 403) or "unauthenticated" in text or "permission_denied" in text or "api key" in text:
        return AUTH

    if _is_timeout_or_network(exc):
        return TRANSIENT
    if code in (500, 502, 503, 504) or "unavailable" in text or "internal error" in text:
        return TRANSIENT

    # 400 / invalid argument / safety block — not a key problem
    return FATAL


def _retry_delay_secs(exc: BaseException) -> float | None:
    """Parse a server-suggested retry delay (e.g. ``retryDelay: "46s"``) if present."""
    text = str(exc)
    m = re.search(r"retry_?delay['\"]?\s*[:{]?\s*['\"]?\s*(?:seconds:\s*)?(\d+)", text, re.IGNORECASE)
    return float(m.group(1)) if m else None


def _backoff(attempt: int) -> float:
    return min(_BACKOFF_BASE * (2 ** (attempt - 1)), _BACKOFF_CAP)


# ───────────────────────────── call wrapper ─────────────────────────────────
async def call_with_rotation(
    fn: Callable[[], Awaitable[T]],
    *,
    max_attempts: int | None = None,
    pool: KeyPool | None = None,
) -> T:
    """Run `fn` (which builds its LLM via `get_llm`, reading the current key) and
    retry across the pool per the §6 policy. `fn` must be an async thunk.

    The wrapper acts on the *current* key (the one `fn` just used). On a key
    failure it adjusts the pool (rotate/cool/drop) and re-invokes `fn` — never
    mid-step (spec §6 rotation granularity).
    """
    pool = pool or get_pool()
    if max_attempts is None:
        max_attempts = len(pool) + _TRANSIENT_RETRIES_BEFORE_ROTATE + 2

    transient_tries = 0
    last_exc: BaseException | None = None

    for attempt in range(1, max_attempts + 1):
        if pool.all_dead():
            raise AllKeysExhausted("all Gemini keys exhausted") from last_exc

        idx = pool.current_index()
        failing_key = pool.current()
        try:
            return await fn()
        except AllKeysExhausted:
            raise
        except BaseException as exc:  # noqa: BLE001 - classified, re-raised or retried
            last_exc = exc
            category = classify_error(exc)
            logger.warning(
                "llm call failed: key_index=%d category=%s attempt=%d/%d code=%s",
                idx, category, attempt, max_attempts, _status_code(exc),
            )

            if category == FATAL:
                raise

            if category == AUTH:
                pool.drop(failing_key)            # permanent; advances off it
            elif category == QUOTA_DAILY:
                delay = max(_retry_delay_secs(exc) or 0.0, _DAILY_COOL_SECS)
                pool.cool(failing_key, delay)
                _safe_rotate(pool)
            elif category == RATE:
                delay = _retry_delay_secs(exc) or _RATE_COOL_SECS
                pool.cool(failing_key, delay)
                _safe_rotate(pool)
            elif category == TRANSIENT:
                transient_tries += 1
                await asyncio.sleep(_backoff(transient_tries))
                if transient_tries >= _TRANSIENT_RETRIES_BEFORE_ROTATE:
                    _safe_rotate(pool)
                    transient_tries = 0
            # loop and retry

    if pool.all_dead():
        raise AllKeysExhausted("all Gemini keys exhausted") from last_exc
    assert last_exc is not None
    raise last_exc


def _safe_rotate(pool: KeyPool) -> None:
    """Rotate, tolerating an exhausted pool (the loop re-checks `all_dead`)."""
    try:
        pool.rotate()
    except AllKeysExhausted:
        pass
