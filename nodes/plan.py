"""plan node (Orchestrator/Planner) — spec §5.1, §2 multimodal, ADR-006/017.

Agentic node: combined multimodal extract + decompose in one call (response_format
= PlanOutput), with the `relook_visual` tool for manifest files. Resets the turn
working state and folds the plan output (subqueries + [[VISUAL_INSIGHTS]] blocks)
into the conversation history.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage

from config import get_settings
from multimodal import file_content_part, register, render_visual_block
from nodes.agent_utils import last_human_text, run_agent
from prompts import PLAN, SYSTEM
from schemas import PlanOutput
from state import GraphState
from tools import make_relook_tool


def _turn_number(messages: list[AnyMessage]) -> int:
    """1-based count of human turns so far (the current question included)."""
    return sum(1 for m in messages if getattr(m, "type", None) == "human") or 1


async def plan_node(state: GraphState) -> dict:
    s = get_settings()
    messages = state["messages"]
    question = last_human_text(messages)
    attachment_paths = state.get("attachment_paths") or []

    # register newly attached files in the manifest (metadata only)
    new_artifacts = register(attachment_paths, _turn_number(messages)) if attachment_paths else []
    all_artifacts = list(state.get("artifacts") or []) + new_artifacts

    # fold any newly attached files onto the last human message for the (combined
    # extract + decompose) multimodal call — raw bytes are NOT persisted (§2)
    agent_messages: list[AnyMessage] = list(messages)
    if attachment_paths:
        parts = [{"type": "text", "text": question}] + [file_content_part(p) for p in attachment_paths]
        agent_messages = list(messages[:-1]) + [HumanMessage(content=parts)]

    prompt = SYSTEM + "\n\n" + PLAN.format(max_subtasks=s.max_subtasks)
    relook = make_relook_tool(all_artifacts)
    result = await run_agent(
        "plan",
        tools=[relook],
        response_format=PlanOutput,
        messages=agent_messages,
        prompt=prompt,
        settings=s,
    )
    plan_out: PlanOutput = result["structured_response"]
    subqueries = plan_out.subqueries[: s.max_subtasks]      # defensive MECE cap

    # plan message for history: pinned visual blocks (§9) + the subquery summary (§3)
    blocks = [render_visual_block(vi) for vi in plan_out.visual_insights]
    if subqueries:
        summary = "Plan — subqueries this turn:\n" + "\n".join(
            f"- SQ{sq.id}: {sq.text} (scope: {sq.scope})" for sq in subqueries
        )
    else:
        summary = "Plan — the question is answerable from known facts; no new research needed."
    plan_message = AIMessage(content="\n\n".join(blocks + [summary]))

    return {
        "subqueries": subqueries,
        "artifacts": new_artifacts,     # reducer appends (never reset)
        "findings": None,               # reset turn working state
        "verified": None,               # reset
        "retry_list": [],
        "iteration": 0,
        "messages": [plan_message],
    }
