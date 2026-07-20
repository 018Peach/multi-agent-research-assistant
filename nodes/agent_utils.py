"""Shared helpers for agentic nodes (spec §5, §6, ADR-019).

`run_agent` builds a `create_react_agent` per invocation (so key rotation can
rebuild it), enforces the per-agent bounds — `recursion_limit = 2*max_steps + 1`
plus a hard `max_tool_calls` volume cap via a counting tool wrapper — and runs it
through `call_with_rotation`.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AnyMessage
from langchain_core.tools import BaseTool, StructuredTool

from config import Settings, agent_bounds

logger = logging.getLogger("nodes.agent")


def message_text(message_or_content: Any) -> str:
    """Extract the plain answer text from a message or content value, dropping
    `thinking` blocks (content may be a str or a list of content-block dicts; P0)."""
    content = getattr(message_or_content, "content", message_or_content)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text" and block.get("text"):
                    parts.append(block["text"])
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content)


def last_human_text(messages: list[AnyMessage]) -> str:
    """Text of the most recent human message (the current question)."""
    for msg in reversed(messages):
        if getattr(msg, "type", None) == "human":
            return message_text(msg)
    return ""


def make_bounded_tools(
    tools: list[BaseTool], max_tool_calls: int, counter: dict | None = None
) -> list[BaseTool]:
    """Wrap tools with a shared counter that refuses calls past `max_tool_calls`
    (the hard volume cap of ADR-019). The counter is shared across rebuilds within
    one node invocation (including resumes) so the cap stays honest."""
    counter = counter if counter is not None else {"n": 0}

    def wrap(tool: BaseTool) -> BaseTool:
        async def _acall(**kwargs: Any) -> Any:
            counter["n"] += 1
            if counter["n"] > max_tool_calls:
                return (
                    f"Tool-call budget ({max_tool_calls}) exceeded. Do not call any more "
                    "tools; produce your final structured answer now from what you have."
                )
            return await tool.ainvoke(kwargs)

        return StructuredTool.from_function(
            coroutine=_acall,
            name=tool.name,
            description=tool.description,
            args_schema=tool.args_schema,
        )

    return [wrap(t) for t in tools]


def _empty_response(model: type) -> Any:
    """An instance of `model` with every (list) field empty — the graceful partial
    result when an agent hits its step cap (spec §6). Works for PlanOutput /
    FindingList / GradedFindingList (all list-valued containers)."""
    empty = {name: [] for name in model.model_fields}
    try:
        return model(**empty)
    except Exception:  # noqa: BLE001 - last-resort bypass of validation
        return model.model_construct(**empty)


async def run_agent(
    node: str,
    *,
    tools: list[BaseTool],
    response_format: type,
    messages: list[AnyMessage],
    prompt: str,
    settings: Settings,
) -> dict:
    """Build + run an agentic node, returning the agent result dict (read
    `result["structured_response"]`).

    Key rotation is **per model call with resume** (spec §6.2, ADR-003): the agent
    is compiled with a per-invocation inner checkpointer + thread; the first attempt
    runs the input, and any retry after a key failure rebuilds the agent on the next
    key and **resumes from the last checkpoint** (`ainvoke(None)`) — so a mid-loop
    429 costs ~one model call, not the whole agent. Bounds reset per invocation (§6).
    """
    # Imported lazily so unit tests can monkeypatch this function without importing
    # langgraph/LLM machinery.
    import uuid

    from langchain_core.exceptions import OutputParserException
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.errors import GraphRecursionError
    from langgraph.prebuilt import create_react_agent
    from pydantic import ValidationError

    from llm.client import call_with_rotation, get_llm

    max_steps, max_tool_calls = agent_bounds(settings, node)

    def _degraded() -> dict:
        return {"structured_response": _empty_response(response_format), "messages": []}

    # Outer loop = schema-validation retry (§10): a malformed structured output is
    # retried once with a fresh agent run, then degraded. The inner key-rotation +
    # resume (call_with_rotation) lives within each attempt.
    for schema_attempt in range(2):
        saver = MemorySaver()
        inner_cfg = {
            "configurable": {"thread_id": uuid.uuid4().hex},
            "recursion_limit": 2 * max_steps + 1,
        }
        tool_counter: dict = {"n": 0}      # shared across resumes (honest volume cap)
        started = {"yes": False}

        async def _run() -> dict:
            # rebuilt each attempt so the next key is picked up; the checkpointer +
            # shared tool_counter carry progress across rebuilds.
            bounded = make_bounded_tools(tools, max_tool_calls, tool_counter) if tools else []
            agent = create_react_agent(
                get_llm(node),
                tools=bounded,
                prompt=prompt,
                response_format=response_format,
                checkpointer=saver,
            )
            if not started["yes"]:
                started["yes"] = True
                return await agent.ainvoke({"messages": messages}, config=inner_cfg)
            return await agent.ainvoke(None, config=inner_cfg)   # resume on the next key

        try:
            result = await call_with_rotation(_run)
        except GraphRecursionError:
            # exhausted step budget → partial (empty) result, not a crash (§6/ADR-019)
            logger.warning("agent '%s' hit its step cap; returning an empty result", node)
            return _degraded()
        except (ValidationError, OutputParserException) as exc:
            if schema_attempt == 0:
                logger.warning("agent '%s' structured output invalid (%s); retrying once",
                               node, type(exc).__name__)
                continue
            logger.warning("agent '%s' structured output invalid after retry; degrading", node)
            return _degraded()

        if not isinstance(result.get("structured_response"), response_format):
            if schema_attempt == 0:
                logger.warning("agent '%s' produced no valid structured response; retrying once", node)
                continue
            logger.warning("agent '%s' structured response missing after retry; degrading", node)
            return _degraded()
        return result

    return _degraded()
