"""Chainlit app — the live, nested multi-agent trace (spec §8, §8.1, ADR-015).

Consumes `graph.astream_events(version="v2")` and maps events to nested `cl.Step`s
manually: each agent node opens a top-level step (the 3 research branches render as
siblings, keyed by run_id), tool calls nest under their agent, thinking summaries
stream to a "thinking" sub-step. The writer's prose streams into the (open) `write`
step itself, so the answer renders under the writer at the bottom of the live trace.
After the turn it appends the verified findings as Sources + computed caveats there,
and prints the observability summary. Degrades cleanly on `AllKeysExhausted`.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import time
import uuid

import chainlit as cl
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from config import get_settings
from graph import build_graph
from llm.client import TRANSIENT, classify_error
from llm.keys import AllKeysExhausted, get_pool
from observability import TraceCollector, step_trace
from ui_events import AGENT_NODES, is_agent_start, owning_agent_run, split_thinking_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

_SETTINGS = get_settings()
_UPLOAD_DIR = ".runtime/uploads"      # runtime artifacts (DB + uploads) live under .runtime/

# Checkpointer opened once and kept alive for the app's lifetime (§8.1).
_GRAPH = None
_SAVER_CM = None


async def _ensure_graph():
    global _GRAPH, _SAVER_CM
    if _GRAPH is None:
        os.makedirs(os.path.dirname(_SETTINGS.db_path) or ".", exist_ok=True)  # sqlite won't make parent dirs
        _SAVER_CM = AsyncSqliteSaver.from_conn_string(_SETTINGS.db_path)
        saver = await _SAVER_CM.__aenter__()
        _GRAPH = build_graph(_SETTINGS, saver)
        logger.info("graph compiled; checkpointer at %s", _SETTINGS.db_path)
    return _GRAPH


def _is_image_or_pdf(element) -> bool:
    mime = (getattr(element, "mime", None) or "").lower()
    name = (getattr(element, "name", None) or "").lower()
    return mime.startswith("image/") or mime == "application/pdf" or name.endswith(
        (".png", ".jpg", ".jpeg", ".webp", ".gif", ".pdf")
    )


def _save_upload(element) -> str:
    """Copy a Chainlit upload to a stable local path so `relook_visual` can re-open
    it on later turns (§9). Returns the saved path."""
    os.makedirs(_UPLOAD_DIR, exist_ok=True)
    dest = os.path.join(_UPLOAD_DIR, f"{uuid.uuid4().hex[:8]}_{element.name}")
    shutil.copy(element.path, dest)
    return dest


def _domain(url: str) -> str:
    """Short display label for a URL (its host), so links don't show long raw URLs."""
    from urllib.parse import urlparse

    try:
        return urlparse(url).netloc or url
    except Exception:  # noqa: BLE001
        return url


def _soften_visual_markup(text: str) -> str:
    """Turn the machine-readable `[[VISUAL_INSIGHTS id=… source="…" type=…]]` … markers
    into a clean display heading, so the plan step shows the extracted vision data as
    legible markdown (not the raw pin markup)."""
    def _hdr(m: re.Match) -> str:
        src = re.search(r'source="([^"]*)"', m.group(0))
        return f"**Extracted from {src.group(1)}**" if src else "**Visual insight**"

    text = re.sub(r"\[\[VISUAL_INSIGHTS[^\]]*\]\]", _hdr, text)
    return text.replace("[[/VISUAL_INSIGHTS]]", "").strip()


def _plan_step_output(output: dict) -> str:
    """Plan trace step body: the pinned visual-insight block(s) + the subquery list —
    i.e. the human-readable `plan_message` the node folds into history — never the raw
    structured JSON handoff (§5, P9 fix)."""
    msgs = output.get("messages") or []
    content = getattr(msgs[0], "content", "") if msgs else ""
    if not isinstance(content, str):
        return ""
    return _soften_visual_markup(content)


def _node_summary(node: str | None, output) -> str:
    """Summary of an agent node's result for its trace step (avoids dumping the raw
    structured handoff into the UI). Plan shows its vision extraction + subqueries;
    research/critic show a one-liner."""
    if not isinstance(output, dict):
        return ""
    if node == "plan":
        return _plan_step_output(output)
    if node == "research":
        return f"Gathered {len(output.get('findings') or [])} finding(s)."
    if node == "critic":
        v, r = len(output.get("verified") or []), len(output.get("retry_list") or [])
        return f"Verified {v}; {r} subquery(ies) flagged for retry."
    return ""


class TurnTrace:
    """Holds the per-turn UI state and maps each `astream_events` event to it."""

    def __init__(self) -> None:
        # Agent steps are TOP-LEVEL `cl.Step`s — Chainlit streams their nested details
        # (tool calls, thinking) to the browser LIVE. The final answer streams into the
        # `write` step itself (kept open), so it renders at the bottom of the trace,
        # under the writer — giving live streaming AND a trace-then-answer layout.
        self.write_step: cl.Step | None = None          # the writer step — answer streams here
        self.answer_msg: cl.Message | None = None        # only for error / degenerate notices
        self.agent_steps: dict[str, cl.Step] = {}       # run_id -> agent step
        self.node_of: dict[str, str] = {}               # run_id -> node name
        self.thinking_steps: dict[str, cl.Step] = {}    # agent run_id -> thinking step
        self.tool_steps: dict[str, cl.Step] = {}        # tool run_id -> tool step
        self.start_times: dict[str, float] = {}         # model run_id -> start
        self.tool_counts: dict[str, int] = {}           # agent run_id -> tool calls
        self.collector = TraceCollector()

    # Step labels + Lucide icon names (rendered by Chainlit's frontend) — no emoji.
    _LABELS = {"plan": "plan", "research": "research", "critic": "critic", "write": "write"}
    _ICONS = {"plan": "compass", "research": "search", "critic": "scale", "write": "pen-line"}
    _TOOL_ICONS = {"web_search": "globe", "fetch_page": "file-text", "relook_visual": "eye"}

    async def ensure_answer(self) -> cl.Message:
        """A standalone message — used only to surface an error / a degenerate no-writer
        turn. The normal answer streams into the writer step (top-level, live)."""
        if self.answer_msg is None:
            self.answer_msg = cl.Message(content="")
            await self.answer_msg.send()
        return self.answer_msg

    async def close_open_steps(self) -> None:
        """Finalize any steps still open when a turn fails, so the nested trace stops
        spinning. `update()` clears each step's `streaming` flag (which drives the UI
        loader); `is_error` marks it as interrupted. Best-effort — never raises."""
        open_steps = (
            list(self.tool_steps.values())
            + list(self.thinking_steps.values())
            + list(self.agent_steps.values())
        )
        for step in open_steps:
            try:
                step.is_error = True
                if not step.output:
                    step.output = "interrupted"
                await step.update()
            except Exception:  # noqa: BLE001 - best-effort cleanup
                pass

    async def _thinking_step(self, agent_run: str) -> cl.Step:
        if agent_run not in self.thinking_steps:
            ts = cl.Step(name="thinking", type="llm", icon="brain",
                         parent_id=self.agent_steps[agent_run].id)
            await ts.send()
            self.thinking_steps[agent_run] = ts
        return self.thinking_steps[agent_run]

    async def handle(self, ev: dict) -> None:
        et = ev["event"]

        if is_agent_start(ev):
            node, rid = ev["name"], ev["run_id"]
            # top-level step (live nested details); the writer step stays open so the
            # answer streamed into it is visible without expanding.
            step = cl.Step(name=self._LABELS.get(node, node), type="run",
                           icon=self._ICONS.get(node), default_open=(node == "write"))
            await step.send()
            self.agent_steps[rid] = step
            self.node_of[rid] = node
            self.tool_counts[rid] = 0
            if node == "write":
                self.write_step = step

        elif et == "on_chain_end" and ev["run_id"] in self.agent_steps:
            step = self.agent_steps[ev["run_id"]]
            summary = _node_summary(self.node_of.get(ev["run_id"]), (ev.get("data") or {}).get("output"))
            if summary:
                step.output = summary
            await step.update()

        elif et == "on_tool_start":
            owner = owning_agent_run(ev, self.agent_steps)
            parent_id = self.agent_steps[owner].id if owner else None
            tname = ev.get("name", "tool")
            tstep = cl.Step(name=tname, type="tool", parent_id=parent_id,
                            icon=self._TOOL_ICONS.get(tname, "wrench"))
            tstep.input = str((ev.get("data") or {}).get("input", ""))[:500]
            await tstep.send()
            self.tool_steps[ev["run_id"]] = tstep
            if owner:
                self.tool_counts[owner] = self.tool_counts.get(owner, 0) + 1

        elif et == "on_tool_end" and ev["run_id"] in self.tool_steps:
            tstep = self.tool_steps[ev["run_id"]]
            tstep.output = str((ev.get("data") or {}).get("output", ""))[:2000]
            await tstep.update()

        elif et == "on_chat_model_start":
            self.start_times[ev["run_id"]] = time.time()

        elif et == "on_chat_model_stream":
            # the inner structured-output node streams the raw JSON handoff
            # (PlanOutput/FindingList/GradedFindingList) — never render it (§5).
            if (ev.get("metadata") or {}).get("langgraph_node") == "generate_structured_response":
                return
            owner = owning_agent_run(ev, self.agent_steps)
            if owner is None:
                return
            thinking, text = split_thinking_text(ev["data"]["chunk"].content)
            if thinking:
                await (await self._thinking_step(owner)).stream_token(thinking)
            # only the writer's prose is user-facing; plan/research/critic text is
            # internal reasoning/handoff, shown instead as thinking + tools + a summary.
            # The answer streams into the (open) writer step → renders under the writer.
            if text and self.node_of.get(owner) == "write" and self.write_step is not None:
                await self.write_step.stream_token(text)

        elif et == "on_chat_model_end":
            owner = owning_agent_run(ev, self.agent_steps)
            node = self.node_of.get(owner, "?") if owner else "?"
            latency_ms = (time.time() - self.start_times.get(ev["run_id"], time.time())) * 1000
            output = (ev.get("data") or {}).get("output")
            self.collector.add(step_trace(
                node,
                usage_metadata=getattr(output, "usage_metadata", None),
                latency_ms=latency_ms,
                key_index=get_pool().current_index(),       # best-effort current key
                tool_calls=self.tool_counts.get(owner, 0) if owner else 0,
                settings=_SETTINGS,
            ))


@cl.on_chat_start
async def on_chat_start() -> None:
    await _ensure_graph()
    cl.user_session.set("thread_id", cl.context.session.id)
    await cl.Message(
        content=(
            "**Multi-Agent Research Assistant.** Ask a research question — optionally "
            "attach a chart or PDF. You'll see the agents (plan → parallel research → "
            "critic → write) work live, then a cited answer."
        )
    ).send()


@cl.on_message
async def on_message(msg: cl.Message) -> None:
    graph = await _ensure_graph()
    tid = cl.user_session.get("thread_id")

    paths = [_save_upload(el) for el in (msg.elements or []) if _is_image_or_pdf(el)]
    inputs = {"messages": [HumanMessage(content=msg.content)], "attachment_paths": paths}
    cfg = {"configurable": {"thread_id": tid}, "recursion_limit": _SETTINGS.recursion_limit}

    tracer = TurnTrace()

    try:
        async for ev in graph.astream_events(inputs, version="v2", config=cfg):
            await tracer.handle(ev)
    except AllKeysExhausted:
        await tracer.close_open_steps()
        answer_msg = await tracer.ensure_answer()
        answer_msg.content = (
            "⚠️ All Gemini API keys are currently rate-limited / out of quota. "
            "Please try again in a little while."
        )
        await answer_msg.update()
        tracer.collector.print_summary()
        return
    except Exception as e:  # noqa: BLE001 - surface a clean message, log the detail
        logger.exception("turn failed")
        await tracer.close_open_steps()
        answer_msg = await tracer.ensure_answer()
        if classify_error(e) == TRANSIENT:
            # model-overload / 503 / network — known transient, retrying helps (§6)
            answer_msg.content = (
                "⚠️ The model is temporarily overloaded (the provider returned a 503 / "
                "service-unavailable). This is usually a brief spike — please try again "
                "in a moment."
            )
        else:
            answer_msg.content = f"⚠️ Something went wrong while researching: {type(e).__name__}."
        await answer_msg.update()
        return

    # post-run: Sources (verified findings) + computed caveats (§8.1, §5.4), appended
    # under the streamed answer inside the writer step.
    snapshot = await graph.aget_state(cfg)
    verified = snapshot.values.get("verified", []) or []
    subqueries = snapshot.values.get("subqueries", []) or []

    extra = ""
    # Sources as a clean markdown section with host-labelled links (no raw long URLs)
    if verified:
        lines = ["\n\n**Sources**"]
        for i, f in enumerate(verified, 1):
            lines.append(f"{i}. {f.claim} — [{_domain(f.source_url)}]({f.source_url})")
        extra += "\n".join(lines)

    verified_ids = {f.subquery_id for f in verified}
    missing = [sq for sq in subqueries if sq.id not in verified_ids]
    if missing:
        extra += (
            "\n\n---\n**Caveats:** could not verify this turn — "
            + "; ".join(sq.text for sq in missing)
            + "."
        )

    if tracer.write_step is not None:
        if not (tracer.write_step.output or "").strip():
            await tracer.write_step.stream_token("I couldn't produce a verified answer this turn.")
        if extra:
            await tracer.write_step.stream_token(extra)
        await tracer.write_step.update()
    else:
        # writer never ran (degenerate) — surface via a standalone message
        msg = await tracer.ensure_answer()
        msg.content = "I couldn't produce a verified answer this turn." + extra
        await msg.update()

    tracer.collector.print_summary()
    logger.info("turn cost ≈ $%.6f", tracer.collector.total_cost)
