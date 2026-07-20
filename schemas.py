"""Pydantic v2 data models — the single source of truth for structured data
(spec §3.1). Agentic nodes emit the ``*List`` / ``PlanOutput`` containers via
``response_format``; the writer streams prose and has no model (spec §5.4).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Subquery(BaseModel):
    """One MECE slice of the research task, produced by `plan` (spec §5.1)."""

    id: int
    text: str
    scope: str                       # one-line MECE scope


class SearchResult(BaseModel):
    """A normalised web-search hit; every provider maps to this (spec §7.1)."""

    title: str
    url: str
    snippet: str
    provider: Literal["tavily", "exa", "gemini"]


class Finding(BaseModel):
    """A specific claim with its supporting source, emitted by `research`
    (spec §5.2). The critic later sets `confidence` / `status` / `issue`."""

    subquery_id: int
    claim: str
    source_url: str
    evidence: str = ""               # snippet / fetched excerpt
    confidence: float | None = None  # set by critic
    status: Literal["approved", "failed"] | None = None
    issue: str | None = None         # critic's reason if failed


class GradedFinding(BaseModel):
    """The critic's per-finding judgement (structured output, spec §5.3)."""

    subquery_id: int
    claim: str
    source_url: str
    grounded: bool
    confidence: float = Field(ge=0.0, le=1.0)
    issue: str | None = None


class RetryBrief(BaseModel):
    """Targeted repair brief for a failed subquery — drives repair-mode
    research (spec §5.3, ADR-016)."""

    subquery_id: int
    failed_claims: list[str]
    reason: str
    rejected_sources: list[str] = Field(default_factory=list)


class VisualInsight(BaseModel):
    """Structured extraction of an uploaded chart/PDF (spec §3.1, §9)."""

    id: str                          # "v1", "v2", …
    source: str                      # e.g. "TRAI 2025"
    type: Literal["image", "pdf"]
    extracted_data: str              # the table/figures as markdown text
    labels: list[str] = Field(default_factory=list)
    trends: list[str] = Field(default_factory=list)
    pages_read: list[int] | None = None    # PDFs only
    caveats: list[str] = Field(default_factory=list)


class Artifact(BaseModel):
    """Manifest entry for an uploaded file — metadata only, no bytes
    (spec §3.1, §9.3)."""

    file_id: str
    local_path: str
    type: Literal["image", "pdf"]
    descriptor: str
    turn: int


class PlanOutput(BaseModel):
    """`plan`'s structured output: subqueries + any newly-extracted visuals
    (spec §5.1)."""

    subqueries: list[Subquery]
    visual_insights: list[VisualInsight] = Field(default_factory=list)


class FindingList(BaseModel):
    """`research`'s structured output container (`response_format`, spec §5.2)."""

    findings: list[Finding]


class GradedFindingList(BaseModel):
    """`critic`'s structured output container (`response_format`, spec §5.3)."""

    items: list[GradedFinding]
