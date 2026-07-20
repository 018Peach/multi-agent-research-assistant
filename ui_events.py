"""Pure helpers for mapping `astream_events` to the nested UI trace (spec §8).

Kept free of Chainlit so the routing logic — which is the subtle part (attributing
inner tool/model events to the right parallel agent branch, splitting thinking from
output) — is unit-testable. `app.py` consumes these.
"""

from __future__ import annotations

AGENT_NODES: tuple[str, ...] = ("plan", "research", "critic", "write")


def is_agent_start(event: dict) -> bool:
    """True for the `on_chain_start` of one of our graph agent nodes (the events
    that open a top-level trace step). Inner react-agent sub-runs have other names."""
    return event.get("event") == "on_chain_start" and event.get("name") in AGENT_NODES


def owning_agent_run(event: dict, agent_run_ids) -> str | None:
    """Return the agent-node run_id this event belongs to: the event's own run_id if
    it IS an agent run, else the agent run_id found in its `parent_ids` chain. This
    is what routes the 3 concurrent research branches' nested events into their own
    sibling steps (validated: parent_ids cleanly separates parallel branches)."""
    rid = event.get("run_id")
    if rid in agent_run_ids:
        return rid
    for parent in event.get("parent_ids", []) or []:
        if parent in agent_run_ids:
            return parent
    return None


def split_thinking_text(content) -> tuple[str, str]:
    """Split a streamed chunk's content into (thinking, output) text. Content may be
    a bare string or a list of content-block dicts; Gemini thought summaries arrive
    as `{"type": "thinking"}` blocks, answer text as `{"type": "text"}` (spec §8/§9,
    P0 finding)."""
    if isinstance(content, str):
        return "", content
    if not isinstance(content, list):
        return "", str(content) if content else ""
    thinking: list[str] = []
    text: list[str] = []
    for block in content:
        if isinstance(block, dict):
            btype = block.get("type")
            if btype == "thinking":
                thinking.append(block.get("thinking") or block.get("text") or "")
            elif btype == "text":
                text.append(block.get("text") or "")
        elif isinstance(block, str):
            text.append(block)
    return "".join(thinking), "".join(text)
