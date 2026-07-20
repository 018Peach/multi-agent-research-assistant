"""research node (Research) — spec §5.2, ADR-012/016.

One parallel branch per `Send`. Input is a `ResearchInput` (subquery + optional
repair brief), NOT the shared conversation. Agentic (web_search + fetch_page),
output via response_format=FindingList. Repair mode when a brief is present.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from config import get_settings
from nodes.agent_utils import run_agent
from prompts import REPAIR_BLOCK, RESEARCH, SYSTEM
from schemas import FindingList
from state import ResearchInput
from tools import fetch_page, web_search


async def research_node(payload: ResearchInput) -> dict:
    s = get_settings()
    sq = payload["subquery"]
    brief = payload.get("brief")

    repair = ""
    if brief is not None:
        repair = REPAIR_BLOCK.format(
            failed_claims=brief.failed_claims,
            reason=brief.reason,
            rejected_sources=brief.rejected_sources,
        )
    human = RESEARCH.format(
        subquery_text=sq.text,
        subquery_scope=sq.scope,
        repair_block=repair,
        subquery_id=sq.id,
    )

    result = await run_agent(
        "research",
        tools=[web_search, fetch_page],
        response_format=FindingList,
        messages=[HumanMessage(content=human)],
        prompt=SYSTEM,
        settings=s,
    )
    findings = result["structured_response"].findings
    for f in findings:
        f.subquery_id = sq.id           # enforce the routing tag (§5.2)
    return {"findings": findings}       # reducer appends across branches
