"""Per-step traces, cost estimation, and the end-of-run summary table (spec §11).

`StepTrace` records one model call's tokens/latency/cost/key. A `TraceCollector`
accumulates them over a turn and prints an aggregated per-node table — the data
source for the §10 monitoring narrative (quality = confidence/eval, cost =
tokens×price, latency = per-node ms). Token counts come from each response's
`usage_metadata`; the **key index** is recorded, never the key (spec §6 security).
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

from config import Settings, get_settings


@dataclass
class StepTrace:
    """One model call's accounting (spec §11). `output_tokens` already includes
    thinking tokens (billed as output); `thinking_tokens` is reported separately."""

    node: str
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0           # includes thinking tokens (billed as output)
    cached_input_tokens: int = 0
    thinking_tokens: int = 0
    est_cost_usd: float = 0.0
    key_index: int = -1              # NEVER the key itself
    iteration: int = 0
    tool_calls: int = 0


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
    settings: Settings | None = None,
) -> float:
    """Estimated USD cost (spec §11, E26): input+output priced per million, minus a
    cache discount — cached input is billed ≈25%, so subtract 75% of its input price.
    `output_tokens` already includes thinking tokens; prices unset → 0."""
    s = settings or get_settings()
    price_in = s.price_input_per_m or 0.0
    price_out = s.price_output_per_m or 0.0
    base = (input_tokens * price_in + output_tokens * price_out) / 1e6
    cache_discount = cached_input_tokens * 0.75 * price_in / 1e6
    return max(base - cache_discount, 0.0)


def extract_usage(usage_metadata: dict | None) -> dict:
    """Pull token counts from a LangChain `usage_metadata` dict (Gemini shape:
    `input_token_details.cache_read`, `output_token_details.reasoning`)."""
    u = usage_metadata or {}
    return {
        "input_tokens": int(u.get("input_tokens", 0) or 0),
        "output_tokens": int(u.get("output_tokens", 0) or 0),
        "cached_input_tokens": int((u.get("input_token_details") or {}).get("cache_read", 0) or 0),
        "thinking_tokens": int((u.get("output_token_details") or {}).get("reasoning", 0) or 0),
    }


def step_trace(
    node: str,
    *,
    usage_metadata: dict | None = None,
    latency_ms: float = 0.0,
    key_index: int = -1,
    iteration: int = 0,
    tool_calls: int = 0,
    settings: Settings | None = None,
) -> StepTrace:
    """Build a `StepTrace` from a response's `usage_metadata`, computing cost."""
    s = settings or get_settings()
    tok = extract_usage(usage_metadata)
    cost = estimate_cost(tok["input_tokens"], tok["output_tokens"], tok["cached_input_tokens"], s)
    return StepTrace(
        node=node, latency_ms=latency_ms, est_cost_usd=cost,
        key_index=key_index, iteration=iteration, tool_calls=tool_calls, **tok,
    )


def step_trace_from_chat_end(
    event: dict,
    *,
    node: str | None = None,
    latency_ms: float = 0.0,
    key_index: int = -1,
    iteration: int = 0,
    tool_calls: int = 0,
    settings: Settings | None = None,
) -> StepTrace:
    """Build a `StepTrace` from an `astream_events` `on_chat_model_end` event. The
    app passes `node` (mapped from the outer graph node via run_id); falls back to
    the event's `langgraph_node` metadata (spec §8/§11)."""
    node = node or (event.get("metadata") or {}).get("langgraph_node") or event.get("name", "?")
    output = (event.get("data") or {}).get("output")
    usage = getattr(output, "usage_metadata", None)
    return step_trace(
        node, usage_metadata=usage, latency_ms=latency_ms,
        key_index=key_index, iteration=iteration, tool_calls=tool_calls, settings=settings,
    )


_NODE_ORDER = ["plan", "research", "critic", "write"]


class TraceCollector:
    """Accumulates `StepTrace`s for a turn and renders the end-of-run summary."""

    def __init__(self) -> None:
        self.traces: list[StepTrace] = []

    def add(self, trace: StepTrace) -> None:
        self.traces.append(trace)

    @property
    def total_cost(self) -> float:
        return sum(t.est_cost_usd for t in self.traces)

    def _aggregate(self) -> OrderedDict:
        agg: OrderedDict[str, dict] = OrderedDict()
        for t in self.traces:
            a = agg.setdefault(t.node, {
                "calls": 0, "in": 0, "out": 0, "cached": 0, "think": 0,
                "cost": 0.0, "lat": 0.0, "iter": 0, "tools": 0,
            })
            a["calls"] += 1
            a["in"] += t.input_tokens
            a["out"] += t.output_tokens
            a["cached"] += t.cached_input_tokens
            a["think"] += t.thinking_tokens
            a["cost"] += t.est_cost_usd
            a["lat"] += t.latency_ms
            a["iter"] = max(a["iter"], t.iteration)
            a["tools"] += t.tool_calls
        # canonical node order first, then any extras
        ordered = OrderedDict()
        for n in _NODE_ORDER:
            if n in agg:
                ordered[n] = agg[n]
        for n in agg:
            if n not in ordered:
                ordered[n] = agg[n]
        return ordered

    def summary_table(self) -> str:
        agg = self._aggregate()
        head = (f"{'node':<10}{'calls':>6}{'in':>9}{'out':>9}{'cached':>8}"
                f"{'think':>8}{'cost$':>11}{'lat_ms':>10}{'iter':>5}{'tools':>6}")
        sep = "-" * len(head)
        lines = ["=== Run summary (per agent) ===", head, sep]
        tot = {"calls": 0, "in": 0, "out": 0, "cached": 0, "think": 0, "cost": 0.0, "lat": 0.0, "tools": 0}
        for node, a in agg.items():
            lines.append(
                f"{node:<10}{a['calls']:>6}{a['in']:>9}{a['out']:>9}{a['cached']:>8}"
                f"{a['think']:>8}{a['cost']:>11.6f}{a['lat']:>10.0f}{a['iter']:>5}{a['tools']:>6}"
            )
            for k in ("calls", "in", "out", "cached", "think", "cost", "lat", "tools"):
                tot[k] += a[k]
        lines.append(sep)
        lines.append(
            f"{'TOTAL':<10}{tot['calls']:>6}{tot['in']:>9}{tot['out']:>9}{tot['cached']:>8}"
            f"{tot['think']:>8}{tot['cost']:>11.6f}{tot['lat']:>10.0f}{'':>5}{tot['tools']:>6}"
        )
        return "\n".join(lines)

    def print_summary(self) -> None:
        print(self.summary_table())
