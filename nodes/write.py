"""write node (Summarisation) — spec §5.4, ADR-010.

A single streaming LLM call (no tools, no structured output) over the `verified`
facts + conversation history. Tokens stream to the UI via astream_events (§8).
Citations are the verified findings (rendered as a Sources element by the app).
Caveats are computed deterministically: any subquery with no verified finding.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from config import get_settings
from llm.client import call_with_rotation, get_llm
from nodes.agent_utils import message_text
from prompts import SYSTEM, WRITE
from state import GraphState


async def write_node(state: GraphState) -> dict:
    s = get_settings()
    verified = state.get("verified") or []
    subqueries = state.get("subqueries") or []
    history = list(state["messages"])

    facts = "\n".join(f"- {f.claim} (source: {f.source_url})" for f in verified)
    if not facts:
        facts = "(no verified facts were produced this turn)"
    write_human = (
        f"Verified facts to use (cite each inline):\n{facts}\n\n"
        "Write the final answer to the user's latest question, citing sources inline."
    )
    messages = [SystemMessage(content=SYSTEM + "\n\n" + WRITE), *history, HumanMessage(content=write_human)]

    async def _run():
        return await get_llm("write").ainvoke(messages)

    response = await call_with_rotation(_run)
    answer = message_text(response).strip()

    # graceful degradation: flag subqueries with no verified finding (§5.4, §10)
    verified_ids = {f.subquery_id for f in verified}
    missing = [sq for sq in subqueries if sq.id not in verified_ids]
    if missing:
        answer += (
            "\n\n---\n**Caveats:** the following could not be verified this turn: "
            + "; ".join(sq.text for sq in missing)
            + "."
        )

    return {"messages": [AIMessage(content=answer)]}
