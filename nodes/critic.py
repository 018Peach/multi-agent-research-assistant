"""critic node (Validation/Critic) — spec §5.3, §7, ADR-012.

One batched agentic pass grading every finding (response_format=GradedFindingList,
may fetch_page to verify). Partitions: approved ⇔ grounded AND confidence ≥
CONFIDENCE_THRESHOLD. Accumulates approved into `verified`, builds a `RetryBrief`
for every subquery left without an approved finding, and consumes `findings` (None).
"""

from __future__ import annotations

from collections import defaultdict

from langchain_core.messages import HumanMessage

from config import get_settings
from nodes.agent_utils import last_human_text, run_agent
from prompts import CRITIC, SYSTEM
from schemas import Finding, GradedFindingList, RetryBrief
from state import GraphState
from tools import fetch_page


def _format_findings(question: str, findings: list[Finding]) -> str:
    lines = [f"Question: {question}", "", "Findings to validate:"]
    for i, f in enumerate(findings, 1):
        lines.append(
            f"\n[{i}] subquery_id={f.subquery_id}\nclaim: {f.claim}\n"
            f"source_url: {f.source_url}\nevidence: {f.evidence}"
        )
    return "\n".join(lines)


def _briefs_for_unapproved(subqueries, approved_ids, failed) -> list[RetryBrief]:
    briefs: list[RetryBrief] = []
    for sq in subqueries:
        if sq.id in approved_ids:
            continue
        d = failed.get(sq.id, {"claims": [], "issues": [], "sources": []})
        reason = "; ".join(d["issues"]) or "No grounded findings were produced for this subquery."
        briefs.append(
            RetryBrief(
                subquery_id=sq.id,
                failed_claims=d["claims"],
                reason=reason,
                rejected_sources=list(dict.fromkeys(d["sources"])),  # dedupe, keep order
            )
        )
    return briefs


async def critic_node(state: GraphState) -> dict:
    s = get_settings()
    findings = state.get("findings") or []
    subqueries = state.get("subqueries") or []
    question = last_human_text(state["messages"])

    # subqueries already satisfied in an earlier pass (accumulated `verified` pool)
    # must NOT be re-flagged for retry (matters when MAX_RESEARCH_ITERATIONS > 1).
    prior_ids = {f.subquery_id for f in (state.get("verified") or [])}

    # nothing gathered this pass → unsatisfied subqueries need a retry (§1)
    if not findings:
        return {
            "verified": [],
            "retry_list": _briefs_for_unapproved(subqueries, prior_ids, {}),
            "findings": None,
        }

    result = await run_agent(
        "critic",
        tools=[fetch_page],
        response_format=GradedFindingList,
        messages=[HumanMessage(content=_format_findings(question, findings))],
        prompt=SYSTEM + "\n\n" + CRITIC,
        settings=s,
    )
    graded = result["structured_response"]

    evidence = {(f.subquery_id, f.source_url): f.evidence for f in findings}
    approved: list[Finding] = []
    failed: dict[int, dict] = defaultdict(lambda: {"claims": [], "issues": [], "sources": []})
    for g in graded.items:
        if g.grounded and g.confidence >= s.confidence_threshold:
            approved.append(
                Finding(
                    subquery_id=g.subquery_id,
                    claim=g.claim,
                    source_url=g.source_url,
                    evidence=evidence.get((g.subquery_id, g.source_url), ""),
                    confidence=g.confidence,
                    status="approved",
                )
            )
        else:
            d = failed[g.subquery_id]
            d["claims"].append(g.claim)
            if g.issue:
                d["issues"].append(g.issue)
            if g.source_url:
                d["sources"].append(g.source_url)

    approved_ids = {f.subquery_id for f in approved} | prior_ids
    return {
        "verified": approved,                                       # append approved
        "retry_list": _briefs_for_unapproved(subqueries, approved_ids, failed),
        "findings": None,                                           # consume graded findings
    }
