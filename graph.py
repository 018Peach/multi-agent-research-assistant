"""Graph assembly (spec §4, architecture §1).

Five nodes: plan → (parallel research via `Send`) → critic → bounded retry
(`prepare_retry`, a `Command`-based node that increments `iteration` on re-fire)
→ write. The static `research → critic` edge is the fan-in barrier (critic runs
once after all branches in the superstep). Checkpointed with `AsyncSqliteSaver`.
"""

from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Send

from config import get_settings
from nodes import critic_node, plan_node, research_node, write_node
from state import GraphState, ResearchInput


def route_after_plan(state: GraphState) -> list[Send] | str:
    """Empty subqueries → answerable from known facts → write. Otherwise fan out
    one parallel `research` branch per subquery (spec §4)."""
    if not state["subqueries"]:
        return "write"
    return [
        Send("research", ResearchInput(subquery=sq, brief=None))
        for sq in state["subqueries"]
    ]


def route_after_critic(state: GraphState) -> Literal["prepare_retry", "write"]:
    """Retry while there are failures AND `iteration < MAX_RESEARCH_ITERATIONS`;
    otherwise write (spec §4 iteration semantics)."""
    settings = get_settings()
    if state["retry_list"] and state["iteration"] < settings.max_research_iterations:
        return "prepare_retry"
    return "write"


def prepare_retry(state: GraphState) -> Command[Literal["research"]]:
    """Re-fire ONLY the failed subqueries in repair mode, incrementing `iteration`
    on re-fire and clearing the worklist (spec §4)."""
    by_id = {sq.id: sq for sq in state["subqueries"]}
    sends = [
        Send("research", ResearchInput(subquery=by_id[b.subquery_id], brief=b))
        for b in state["retry_list"]
        if b.subquery_id in by_id
    ]
    return Command(
        update={"iteration": state["iteration"] + 1, "retry_list": []},
        goto=sends,
    )


def build_graph(settings, checkpointer):
    """Wire and compile the graph with the given checkpointer (spec §4, §8.1)."""
    g = StateGraph(GraphState)
    g.add_node("plan", plan_node)
    g.add_node("research", research_node)
    g.add_node("critic", critic_node)
    g.add_node("prepare_retry", prepare_retry)
    g.add_node("write", write_node)

    g.add_edge(START, "plan")
    g.add_conditional_edges("plan", route_after_plan, ["research", "write"])
    g.add_edge("research", "critic")                         # fan-in barrier
    g.add_conditional_edges("critic", route_after_critic, ["prepare_retry", "write"])
    # prepare_retry routes to research via Command(goto=[Send(...)])
    g.add_edge("write", END)
    return g.compile(checkpointer=checkpointer)
