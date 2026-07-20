# Multi-Agent Research Assistant

A general-purpose, chat-based **multi-agent research assistant** (LangGraph + Gemini). It takes a
research problem (optionally with a **chart/PDF**), decomposes it into MECE subqueries, runs
**parallel research agents** that gather web evidence, **validates** every claim with a critic
(grounding + confidence + a bounded retry), and **streams a structured, cited answer** — shown as
a live, nested agent trace. Domain-neutral; **demonstrated on a Customer-Experience (CX) use case**.

```
        user query (+ chart/PDF)
                 │
              ▼  PLAN   ── vision-extract the chart + decompose into ≤3 MECE subqueries
        ┌──────┴───────┐
   RESEARCH × N (parallel)  ── web_search / fetch_page → Findings (tagged by subquery)
        └──────┬───────┘
              ▼  CRITIC  ── grounding + confidence per finding (failed → repair-mode retry)
              ▼  WRITE   ── stream a cited answer from the verified facts (+ caveats)
```

Full design, agent roles/interactions, and a mermaid diagram: **[`docs/architecture.md`](docs/architecture.md)**.

---

## Setup

**Python 3.13** recommended (3.11–3.13). Avoid **3.14** — `uvicorn` isn't 3.14-ready, so the
Chainlit UI serves a blank page. All commands run from this `src/` folder.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                # then set GEMINI_API_KEYS
```

Only **`GEMINI_API_KEYS`** is required (one or more keys, comma-separated —
<https://aistudio.google.com/apikey>). `TAVILY_API_KEY` / `EXA_API_KEY` / `FIRECRAWL_API_KEY` are
optional (search falls back to Gemini's keyless Google Search; `fetch_page` is skipped without
Firecrawl). See `.env.example` for all knobs.

## Run

```bash
chainlit run app.py                 # → http://localhost:8000
#.\.venv\Scripts\chainlit run app.py
```

Ask a research question; to exercise the **multimodal** path, attach a chart/PDF with the button. Watch the agents work live (plan → parallel research → critic → write), then get a cited answer with a **Sources** list; a per-run cost/latency/token summary prints in the terminal.

## Codebase overview

Entry + orchestration:

| File | Responsibility |
|---|---|
| `app.py` | Chainlit app — maps `astream_events` to the live nested agent trace; streams the answer under the writer step. |
| `graph.py` | LangGraph wiring: `plan → research×N (Send) → critic → prepare_retry → write` + `AsyncSqliteSaver`. |
| `config.py` | `Settings` (pydantic-settings from `.env`) + per-node thinking tiers + per-agent bounds. |
| `schemas.py` | Pydantic v2 models for all structured data (Subquery, Finding, GradedFinding, PlanOutput, …). |
| `state.py` | `GraphState` (checkpointed) + reducers (`add_messages`, `extend_or_reset`) + `ResearchInput`. |
| `prompts.py` | Shared `SYSTEM` persona + per-node task prompts. |
| `multimodal.py` | Type-aware Gemini vision extraction → `[[VISUAL_INSIGHTS]]` block + artifact manifest. |
| `ui_events.py` | Pure helpers mapping `astream_events` to the UI (branch attribution, thinking/text split). |

Agents (`nodes/`):

| File | Responsibility |
|---|---|
| `nodes/agent_utils.py` | Builds a bounded `create_react_agent` per call; key-rotation-with-resume; schema-retry; partial-result degradation. |
| `nodes/plan.py` | **Orchestrator/Planner** — vision-extract + decompose into MECE subqueries; resets per-turn state. |
| `nodes/research.py` | **Research** worker (one per branch) — `web_search`/`fetch_page` → Findings; repair mode on retry. |
| `nodes/critic.py` | **Validation** — grades grounding + confidence per finding; approves → `verified`, fails → retry briefs. |
| `nodes/write.py` | **Summarisation** — single streaming call; cited answer + deterministic caveats. |
| `nodes/__init__.py` | Exports the four node callables. |

LLM access (`llm/`) and tools (`tools/`):

| File | Responsibility |
|---|---|
| `llm/keys.py` | Gemini key pool — rotate / cool / drop + health; `AllKeysExhausted`. |
| `llm/client.py` | `get_llm(node)` factory + `call_with_rotation` error-classification policy. |
| `tools/search.py` | `web_search` — Tavily → Exa → Gemini fallback, normalised + untrusted-fenced. |
| `tools/fetch.py` | `fetch_page` — Firecrawl URL → markdown for source verification. |
| `tools/visual.py` | `relook_visual` — scoped re-extraction of a previously uploaded file. |
| `tools/untrusted.py` | `as_untrusted()` — prompt-injection fence wrapping external data as "data, not instructions". |

Observability + assets:

| File | Responsibility |
|---|---|
| `observability/trace.py` | `StepTrace` + cost estimate + per-agent end-of-run summary table. |
| `public/custom.css` | Chainlit theme (refined dark + violet) and long-content wrapping. |
| `.chainlit/config.toml` | Chainlit config (full chain-of-thought, custom CSS, file upload). |
| `chainlit.md` | Intentionally empty (suppresses the default Readme button). |
| `requirements.txt` / `.env.example` | Pinned dependencies / environment template. |

## Deliverables (siblings of this folder)

- **[`docs/architecture.md`](docs/architecture.md)** — architecture overview, mermaid diagram, agent roles/interactions, guardrails, scaling/monitoring, CX.
- **[`samples/`](samples/)** — example research query + the generated output.
- **[`demo-video`](https://drive.google.com/file/d/1IVyQ0UAkuqTY20M7ZflsAlaFyMcTnViM/view?usp=sharing)** — the screen recording.

---

> **Note on tests & evaluation.** This code bundle ships the application only. The development test
> suite (74 deterministic `pytest` cases) and the offline **LLM-judge eval harness** are not
> included here to keep the submission focused — both passed: all 74 tests green, and the eval
> scored **groundedness / coverage / citation-completeness = 1.00 / 1.00 / 1.00** on both golden
> cases. The evaluation methodology (and how runtime guardrails detect hallucinations) is described
> in `docs/architecture.md` §6.
