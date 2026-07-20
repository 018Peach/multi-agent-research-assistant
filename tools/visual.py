"""`relook_visual` tool (plan phase) — re-open a previously uploaded file from the
artifact manifest for a scoped re-extraction (spec §7.3, §9, ADR-017).

Built per-invocation with the current `artifacts` so it can resolve `file_id` ->
`local_path`. Makes a scoped vision call and returns a new `[[VISUAL_INSIGHTS]]`
block, which `plan` persists into the conversation. The safety net for the
PDF / dense-dashboard case (scoped extraction is deliberately partial).
"""

from __future__ import annotations

import logging
import uuid

from langchain_core.tools import tool

from multimodal import extract_visual, render_visual_block
from schemas import Artifact

logger = logging.getLogger("tools.visual")


def make_relook_tool(artifacts: list[Artifact]):
    """Return a `relook_visual` tool bound to the current manifest (spec §7.3)."""

    @tool
    async def relook_visual(file_id: str, focus: str) -> str:
        """Re-open a prior uploaded file (by `file_id` from the manifest) and extract
        `focus`-scoped insights. Returns a [[VISUAL_INSIGHTS]] block."""
        artifact = next((a for a in artifacts if a.file_id == file_id), None)
        if artifact is None:
            known = ", ".join(a.file_id for a in artifacts) or "(none)"
            return f"relook_visual: no file with file_id={file_id}. Known: {known}."
        try:
            vi = await extract_visual(
                artifact.local_path,
                vid=f"v-{uuid.uuid4().hex[:4]}",
                source=artifact.descriptor,
                focus=focus,
            )
        except Exception as e:  # noqa: BLE001 - return a short error, don't kill the loop
            logger.warning("relook_visual failed for %s: %s", file_id, type(e).__name__)
            return f"relook_visual error for {file_id}: {type(e).__name__}: {e}"
        return render_visual_block(vi)

    return relook_visual
