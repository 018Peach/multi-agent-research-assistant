"""Gemini API key pool (spec §6.1, ADR-003).

An equal pool with simple rotate-on-demand. Keys can be **dropped** permanently
(auth/invalid) or **cooled** temporarily (quota exhausted). Security: callers log
the key *index*, never the key value (spec §6).
"""

from __future__ import annotations

import time
from functools import lru_cache


class AllKeysExhausted(RuntimeError):
    """Raised when no healthy key remains — drives graceful degradation (§6, §10)."""


class KeyPool:
    """Equal pool; rotate on demand; track dead/cooling keys (spec §6.1)."""

    def __init__(self, keys: list[str]) -> None:
        if not keys:
            raise ValueError("KeyPool requires at least one key")
        self._keys: list[str] = list(keys)
        self._idx: int = 0
        self._dead: set[int] = set()              # permanently removed (auth)
        self._cool_until: dict[int, float] = {}   # index -> monotonic expiry

    # ── health ────────────────────────────────────────────────────────────
    def _is_healthy(self, i: int) -> bool:
        if i in self._dead:
            return False
        expiry = self._cool_until.get(i)
        if expiry is not None:
            if time.monotonic() >= expiry:
                del self._cool_until[i]           # cooldown elapsed -> healthy
                return True
            return False
        return True

    def _has_healthy(self) -> bool:
        return any(self._is_healthy(i) for i in range(len(self._keys)))

    def all_dead(self) -> bool:
        """True when no healthy key remains (all dropped and/or cooling)."""
        return not self._has_healthy()

    # ── access ────────────────────────────────────────────────────────────
    def current(self) -> str:
        """The current healthy key (advances past it if it just went unhealthy)."""
        if not self._is_healthy(self._idx):
            self._advance()                       # raises if none healthy
        return self._keys[self._idx]

    def current_index(self) -> int:
        """Index of the current key (safe to log; never log the key itself)."""
        return self._idx

    def rotate(self) -> str:
        """Advance to the next healthy key and return it."""
        self._advance()
        return self._keys[self._idx]

    def _advance(self) -> None:
        n = len(self._keys)
        for step in range(1, n + 1):
            j = (self._idx + step) % n
            if self._is_healthy(j):
                self._idx = j
                return
        raise AllKeysExhausted("no healthy Gemini key available")

    # ── state changes ─────────────────────────────────────────────────────
    def drop(self, key: str) -> None:
        """Remove a key permanently (auth/invalid); advance off it if current."""
        for i, k in enumerate(self._keys):
            if k == key:
                self._dead.add(i)
        if not self._is_healthy(self._idx) and self._has_healthy():
            self._advance()

    def cool(self, key: str, secs: float) -> None:
        """Skip a key until ``secs`` from now (quota exhausted); advance if current."""
        until = time.monotonic() + max(0.0, secs)
        for i, k in enumerate(self._keys):
            if k == key:
                self._cool_until[i] = until
        if not self._is_healthy(self._idx) and self._has_healthy():
            self._advance()

    def __len__(self) -> int:
        return len(self._keys)


@lru_cache
def get_pool() -> KeyPool:
    """Process-wide key pool singleton, built from `Settings.gemini_keys` (§6)."""
    from config import get_settings

    return KeyPool(get_settings().gemini_keys)
