"""Multimodal vision: type-aware extraction of an uploaded chart/PDF into a
structured `VisualInsight`, the `[[VISUAL_INSIGHTS]]` block format, and the
artifact manifest (spec §9, ADR-017).

Extraction is **type-aware**: exhaustive for images/charts (the small visual is
fully capturable in one pass), query-scoped for PDFs (relevant pages only, recording
`pages_read`). The `plan` node does its own *combined* extract+decompose call (§5.1);
this module's `extract_visual` powers the `relook_visual` tool (§7.3) and standalone
extraction. The structured `VisualInsight` is rendered as a pinnable text block and
carried in the Main-agent history (§3).
"""

from __future__ import annotations

import base64
import mimetypes
import uuid
from pathlib import Path
from typing import Literal

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from llm.client import call_with_rotation, get_llm
from schemas import Artifact, VisualInsight


# ── type detection + content part ────────────────────────────────────────────
def detect_type(path: str | Path) -> Literal["image", "pdf"]:
    """`"pdf"` for `.pdf`, else `"image"` (spec §9.2). A dense multi-chart
    dashboard is handled as the PDF case via prompting, not a code branch."""
    return "pdf" if str(path).lower().endswith(".pdf") else "image"


def _mime_for(path: str | Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    if mime:
        return mime
    return "application/pdf" if detect_type(path) == "pdf" else "image/png"


def file_content_part(path: str | Path) -> dict:
    """A langchain-google-genai `media` content block (works for image AND pdf):
    base64-inlined bytes + mime type (verified idiom — chat_models §`media`)."""
    data = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    return {"type": "media", "mime_type": _mime_for(path), "data": data}


# ── structured vision output ─────────────────────────────────────────────────
class _VisualExtract(BaseModel):
    """LLM output for a vision extraction (id/source/type are set by the caller)."""

    extracted_data: str = Field(description="The chart/table/figures as markdown text.")
    labels: list[str] = Field(default_factory=list, description="Axis/series/category labels.")
    trends: list[str] = Field(default_factory=list, description="Notable trends or movements.")
    pages_read: list[int] | None = Field(default=None, description="PDF pages read (PDF only).")
    caveats: list[str] = Field(default_factory=list, description="Anything partial/uncertain.")


_IMAGE_PROMPT = (
    "Extract ALL data from the attached chart/image EXHAUSTIVELY. Transcribe the full "
    "underlying table (every row, column and value), all axis labels, the legend, any "
    "annotations, and every visible data point. Put it in `extracted_data` as markdown "
    "(use a table if tabular). List `labels` (axes/series/categories) and the `trends` "
    "you can read. Do not omit any datum."
)


def _pdf_prompt(focus: str) -> str:
    return (
        "Extract data from the attached PDF that is relevant to this focus:\n"
        f"  FOCUS: {focus}\n"
        "Be query-scoped: pull only the figures/pages/sections relevant to the focus "
        "(do not transcribe the whole document). Record the page numbers you actually "
        "read in `pages_read`. Put the relevant content in `extracted_data` as markdown; "
        "list `labels` and `trends`; note anything partial in `caveats`."
    )


async def extract_visual(
    path: str | Path,
    *,
    vid: str,
    source: str,
    focus: str | None = None,
) -> VisualInsight:
    """Make a type-aware Gemini vision call and return a `VisualInsight` (§9.2).

    Exhaustive for images; query-scoped for PDFs (`focus` drives the scope). Wrapped
    in `call_with_rotation` so a key failure rotates and retries (§6).
    """
    vtype = detect_type(path)
    prompt = _IMAGE_PROMPT if vtype == "image" else _pdf_prompt(focus or "the key figures and findings")
    message = HumanMessage(content=[{"type": "text", "text": prompt}, file_content_part(path)])

    async def _run() -> _VisualExtract:
        llm = get_llm("plan", structured=_VisualExtract)
        return await llm.ainvoke([message])

    extract: _VisualExtract = await call_with_rotation(_run)
    return VisualInsight(
        id=vid,
        source=source,
        type=vtype,
        extracted_data=extract.extracted_data,
        labels=extract.labels,
        trends=extract.trends,
        pages_read=extract.pages_read if vtype == "pdf" else None,
        caveats=extract.caveats,
    )


# ── [[VISUAL_INSIGHTS]] block ────────────────────────────────────────────────
def render_visual_block(vi: VisualInsight) -> str:
    """Serialise a `VisualInsight` as the pinnable `[[VISUAL_INSIGHTS]]` block
    (spec §9.1). The marker (not position) makes it preservable through compaction."""
    return (
        f'[[VISUAL_INSIGHTS id={vi.id} source="{vi.source}" type={vi.type}]]\n'
        f"{vi.extracted_data}\n"
        f"labels: {', '.join(vi.labels)}\n"
        f"trends: {', '.join(vi.trends)}\n"
        + (f"pages_read: {vi.pages_read}\n" if vi.pages_read else "")
        + (f"caveats: {', '.join(vi.caveats)}\n" if vi.caveats else "")
        + "[[/VISUAL_INSIGHTS]]"
    )


# ── manifest ─────────────────────────────────────────────────────────────────
def register(paths: list[str], turn: int) -> list[Artifact]:
    """Build manifest entries (metadata only, no bytes) for files attached this
    turn (spec §9.3). The files already live on local disk; `relook_visual` resolves
    `file_id` -> `local_path` from these entries."""
    artifacts: list[Artifact] = []
    for p in paths:
        path = Path(p)
        artifacts.append(
            Artifact(
                file_id=f"file_{uuid.uuid4().hex[:8]}",
                local_path=str(path.resolve()),
                type=detect_type(p),
                descriptor=path.stem,
                turn=turn,
            )
        )
    return artifacts
