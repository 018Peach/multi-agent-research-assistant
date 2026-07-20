"""Graph state + reducers (spec §3.2). `GraphState` is checkpointed per thread;
`ResearchInput` is the small per-branch `Send` payload (not the main state).
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

from schemas import Artifact, Finding, RetryBrief, Subquery


def extend_or_reset(current: list | None, update: list | None) -> list:
    """Reducer: append within a turn; ``None`` resets to ``[]``.

    ``None`` is the reset/consume signal — `plan` resets `findings`/`verified`
    at turn start, and `critic` returns ``findings=None`` to consume what it
    graded so a retry pass sees only fresh findings (spec §3.2).
    """
    return [] if update is None else (current or []) + (update or [])


class GraphState(TypedDict):
    """The checkpointed per-thread state (spec §3.2)."""

    # ── persistent (checkpointed per thread) ──────────────────────────────
    messages: Annotated[list[AnyMessage], add_messages]
    artifacts: Annotated[list[Artifact], extend_or_reset]   # append uploads; never reset

    # ── current-turn input (question = latest HumanMessage in `messages`) ──
    attachment_paths: list[str]            # files attached THIS turn

    # ── turn working state (plan resets each turn) ────────────────────────
    subqueries: list[Subquery]
    findings: Annotated[list[Finding], extend_or_reset]    # parallel fan-in; critic consumes
    verified: Annotated[list[Finding], extend_or_reset]    # accumulates approved this turn
    retry_list: list[RetryBrief]
    iteration: int                         # retries done (0-based)


class ResearchInput(TypedDict):
    """Per-branch `Send` payload — a small, focused schema, NOT the main state
    (LangGraph map-reduce best practice). The branch returns ``{"findings": [...]}``,
    which the parent reduces (spec §3.2, §5.2)."""

    subquery: Subquery
    brief: RetryBrief | None               # repair mode when present
