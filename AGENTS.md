# AGENTS.md

Instructions for AI coding agents working with the Pixeltable Starter Kit.

## Pixeltable Resources

Before modifying this codebase, familiarize yourself with Pixeltable:

- **Core AGENTS.md** — [pixeltable/pixeltable/AGENTS.md](https://github.com/pixeltable/pixeltable/blob/main/AGENTS.md) covers the full SDK: tables, computed columns, views, iterators, UDFs, embedding indexes, and all AI provider integrations.
- **Claude Code Skill** — [pixeltable/pixeltable-skill](https://github.com/pixeltable/pixeltable-skill) gives Claude deep Pixeltable expertise via progressive disclosure (`SKILL.md` → `API_REFERENCE.md`).
- **MCP Server** — [pixeltable/mcp-server-pixeltable-developer](https://github.com/pixeltable/mcp-server-pixeltable-developer) exposes Pixeltable as an MCP server for interactive exploration (tables, queries, Python REPL).
- **Docs** — [docs.pixeltable.com](https://docs.pixeltable.com/) · [SDK Reference](https://docs.pixeltable.com/sdk/latest/pixeltable)

## What This Template Is

A production-ready starter kit demonstrating how to put Pixeltable in production with FastAPI + Pydantic + TypeScript. Three tabs show three interaction patterns:

| Tab | Pattern | Key Pixeltable Features |
|-----|---------|------------------------|
| **Data** | Upload → automatic processing | `create_table`, `create_view` with iterators, `add_computed_column` |
| **Search** | Cross-modal similarity queries | `add_embedding_index`, `.similarity()`, CLIP + sentence-transformers |
| **Agent** | Insert-triggers-pipeline | `pxt.tools`, `invoke_tools`, chained computed columns, `@pxt.query` |

## Project Structure

```
backend/
├── main.py                 FastAPI app (CORS, routers, SPA fallback)
├── config.py               Environment-driven settings (models, prompts, CORS)
├── models.py               Pydantic models (row schemas, result validation, API request/response)
├── functions.py             @pxt.udf definitions (web search via ddgs, context assembly)
├── setup_pixeltable.py      Declarative schema: tables, views, indexes, agent pipeline (no router queries)
├── pyproject.toml           Dependencies managed via uv
└── routers/
    ├── data.py              FastAPIRouter + @pxt.query (upload, list, delete, detail queries)
    ├── search.py            FastAPIRouter + @pxt.query (4 similarity search endpoints)
    └── agent.py             FastAPIRouter + @pxt.query (3 declarative + 1 hand-written agent query)

frontend/src/
├── App.tsx                  Tab navigation (Data / Search / Agent)
├── components/              Page components + shared UI (Button, Badge)
├── lib/api.ts               Typed fetch wrapper + client-side aggregation/fan-in
└── types/index.ts           TypeScript interfaces (PxtQueryResponse<T> + app-specific types)

orchestration/                   Ephemeral batch processing pattern
├── schema.py                    Tables, views, embedding indexes, computed columns
├── pipeline.py                  Batch: ingest → compute → export_sql → exit
├── Dockerfile                   Ephemeral container (PIXELTABLE_HOME=/tmp)
└── docker-compose.yml           Local testing

serving/                         Declarative API serving (zero Python web code)
├── schema.py                    Tables, views, indexes, @pxt.query functions
├── pyproject.toml               Dependencies + pxt serve config ([tool.pixeltable])
├── Dockerfile                   Long-running container
└── docker-compose.yml           Local testing

deploy/
├── fly/                     Fly.io (fly.toml + persistent volume)
├── render/                  Render (Blueprint render.yaml)
├── railway/                 Railway (railway.json + Dockerfile)
├── helm/                    Helm chart (any existing K8s cluster)
├── terraform-k8s/           Terraform + AWS EKS
├── terraform-gke/           Terraform + GCP GKE
├── terraform-aks/           Terraform + Azure AKS
└── aws-cdk/                 CDK + ECS Fargate

.devcontainer/               Dev Container for VS Code / Codespaces
├── devcontainer.json        Python 3.12, Node 20, uv, extensions
└── post-create.sh           Auto-installs backend + frontend deps
```

## Setup

```bash
git clone https://github.com/pixeltable/pixeltable-starter-kit.git
cd pixeltable-starter-kit
cp .env.example .env          # add ANTHROPIC_API_KEY and OPENAI_API_KEY

cd backend
uv sync                       # creates .venv, installs deps including en_core_web_sm
source .venv/bin/activate
python setup_pixeltable.py    # initialize schema (idempotent; set RESET_SCHEMA=true to wipe)
python main.py                # http://localhost:8000

# Frontend (separate terminal)
cd frontend
npm install && npm run dev    # http://localhost:5173
```

Production: `cd frontend && npm run build` then `cd ../backend && python main.py` — serves everything at `:8000`.

## Architectural Decisions

Each decision below is intentional. Don't change it without understanding why.

### Pixeltable IS the data layer

There is no ORM, no SQLAlchemy, no direct PostgreSQL client. Pixeltable handles storage, indexing, transformation, and retrieval. `setup_pixeltable.py` defines the schema (tables, views, computed columns, embedding indexes, agent pipeline). Router-facing `@pxt.query` functions live in each router file.

### Sync endpoints (`def`, not `async def`)

All FastAPI endpoints use `def`, not `async def`. Pixeltable operations are synchronous and thread-safe. Uvicorn runs sync endpoints in a thread pool automatically, which is the correct pattern. Using `async def` would block the event loop.

### No explicit event loop configuration

`uvicorn.run()` is called without `loop="asyncio"`. This lets Uvicorn auto-detect `uvloop` when available, which is faster.

### Schema-as-code

`setup_pixeltable.py` is a flat module — no wrapper function. Importing it creates tables, views, computed columns, embedding indexes, and the agent pipeline (Python's import system guarantees this runs exactly once). Agent-internal `@pxt.query` functions are defined at module level between the tables they reference. Router-facing queries live in each router file, co-located with the `add_query_route` calls that expose them. Every schema call uses `if_exists="ignore"` (with explicit `idx_name`), so re-running never destroys data. Set `RESET_SCHEMA=true` to wipe and recreate. The schema defines:

1. **Document pipeline** — table → `DocumentSplitter` view → sentence-transformer embedding index
2. **Image pipeline** — table → thumbnail computed column → CLIP embedding index
3. **Video pipeline** — table → `FrameIterator` view (keyframes + CLIP) → audio extraction → Whisper transcription → `StringSplitter` view → embedding index
4. **Chat history** — table with embedding index for two-tier memory: conversation-scoped recent history + cross-conversation semantic recall
5. **Agent pipeline** — 11 computed columns: initial LLM call with tools (web search, document search, transcript search) → tool execution → parallel RAG retrieval (docs, images, video frames, chat memory) → conversation-scoped history → context assembly → final LLM call → answer extraction

### Integrated `FastAPIRouter` (v0.6+)

All three routers use Pixeltable's `FastAPIRouter` (a subclass of FastAPI's `APIRouter`). `main.py` imports `setup_pixeltable` (triggering schema init) before importing routers. Each router calls `pxt.get_table()` and defines its own `@pxt.query` functions co-located with `add_query_route` registrations. Only **1 of 20 endpoints** is hand-written:

**`data.py`** — no hand-written endpoints (12 routes):

| Route | Method | Notes |
|-------|--------|-------|
| `/api/data/upload/{document,video}` | `add_insert_route` | `background=True` — returns job handle, client polls `/jobs/{id}` |
| `/api/data/upload/image` | `add_insert_route` | Synchronous (thumbnail + CLIP is fast) |
| `/api/data/delete/{document,image,video}` | `add_delete_route` | Match by primary key (uuid) |
| `/api/data/chunks`, `/frames`, `/transcription` | `add_query_route` (POST) | Detail queries accepting `file_uuid` |
| `/api/data/list/{documents,images,videos}` | `add_query_route` (GET) | Per-table listing |

**`search.py`** — no hand-written endpoints (4 routes):

| Route | Method | Notes |
|-------|--------|-------|
| `/api/search/{documents,images,video-frames,transcripts}` | `add_query_route` (POST) | One per embedding index, accepts `query_text` |

**`agent.py`** — 3 declarative + 1 hand-written:

| Route | Method | Notes |
|-------|--------|-------|
| `/api/agent/conversation` | `add_query_route` (POST) | Messages for a `conversation_id` |
| `/api/agent/messages` | `add_query_route` (GET) | All messages (frontend groups client-side) |
| `/api/agent/delete-conversation` | `add_delete_route` | `match_columns=["conversation_id"]` |
| `/api/agent/query` | **Hand-written** `@router.post` | Input guardrail, response personalization, multi-table side effects (agent + 2× chat_history) |

The frontend (`api.ts`) handles aggregation that was previously done server-side: parallel fetches to granular endpoints, client-side merge/sort/group-by, and deduplication.

### Minimal Pydantic models

`models.py` contains only the models needed by the single hand-written endpoint (`POST /api/agent/query`): `ToolAgentRow` and `ChatHistoryRow` (row schemas for `table.insert()`), `AgentResult` (validates the dict from `return_rows=True` with `extra="ignore"` to extract only the fields the endpoint needs), and `QueryRequest`/`QueryResponse` (API contract). `QueryRequest` accepts optional `temperature`, `max_tokens`, and `system_prompt` for per-request personalization. All other endpoints are declarative — `FastAPIRouter` auto-generates request/response schemas from table columns and `@pxt.query` return types. Query endpoints return `{ "rows": [...] }` automatically.

### Disentangled schema vs. serving

`setup_pixeltable.py` is **pure schema** — a flat module that creates tables, views, indexes, and agent-internal queries on import. Router files are **pure serving** — each gets table references via `pxt.get_table()` and defines `@pxt.query` functions locally, then wires them to `add_query_route`. No cross-file query imports, no wrapper functions, no global state.

### `@pxt.udf` and `@pxt.query` for logic

Business logic lives in Pixeltable functions, not endpoint handlers. `@pxt.udf` (in `functions.py`) for custom transforms like web search and context assembly. `@pxt.query` functions are defined **in each router file** next to the `add_query_route` calls that expose them — they retrieve table references via `pxt.get_table()` at module level. Agent-internal queries (used only by computed columns) live in `setup_pixeltable.py` at module level. The only hand-written endpoint (`POST /api/agent/query`) exists because it performs multi-table inserts with conditional logic that can't be expressed declaratively.

### Agent pipeline as computed columns

The entire tool-calling agent is a chain of `add_computed_column()` calls on the `agent` table. Inserting a row triggers the full pipeline: tool planning → execution → multimodal RAG → context assembly → final answer. The router uses `insert(return_rows=True)` to get computed results directly from the insert (no follow-up query), then validates with `AgentResult.model_validate()` for typed field access.

### Typed frontend

TypeScript interfaces in `types/index.ts` mirror the backend Pydantic models. `lib/api.ts` is a generic typed fetch wrapper — no code generation, no heavy HTTP client. Intentionally simple for a template.

### Containerized deployment

A multi-stage `Dockerfile` builds the frontend and Python runtime into a single image. `docker-compose.yml` runs it locally with named volumes for Pixeltable data. Deployment options live in `deploy/`:

- **`deploy/fly/`** — [Fly.io](https://fly.io): `fly.toml` with persistent volume, auto-scaling, scale-to-zero. Simplest path to production.
- **`deploy/render/`** — [Render](https://render.com): Blueprint (`render.yaml`) for one-click deploy with persistent disk.
- **`deploy/railway/`** — [Railway](https://railway.app): `railway.json` for build/deploy config. Add a volume at `/data/pixeltable`.
- **`deploy/helm/`** — Helm chart for deploying on **any existing K8s cluster**. Creates Secret, PVC, schema init Job (Helm hook), Deployment with health checks, and LoadBalancer Service. No infra provisioning — just `helm install`.
- **`deploy/terraform-k8s/`** — Provisions full AWS stack from scratch: VPC, EKS cluster, ECR, plus K8s resources. Pixeltable data on 50Gi EBS.
- **`deploy/terraform-gke/`** — Same pattern for GCP: VPC, GKE cluster, Artifact Registry. 50Gi Persistent Disk.
- **`deploy/terraform-aks/`** — Same pattern for Azure: Resource Group, AKS cluster, ACR. 50Gi Managed Disk.
- **`deploy/aws-cdk/`** — ECS Fargate behind ALB with EFS for persistent storage. Auto-scales 1–4 tasks.

All configure `PIXELTABLE_HOME=/data/pixeltable` pointing to persistent storage. For large media workloads, set `PIXELTABLE_INPUT_MEDIA_DEST` and `PIXELTABLE_OUTPUT_MEDIA_DEST` to S3/GCS/Azure Blob URIs (see [Pixeltable Configuration](https://docs.pixeltable.com/platform/configuration.md)).

### SPA fallback

`npm run build` outputs to `backend/static/`. FastAPI's catch-all `/{full_path:path}` serves the built frontend. One process, one port in production. In development, Vite's proxy forwards `/api` to the backend.

### `pyproject.toml` + `uv`

Modern Python packaging. `uv sync` creates the venv and installs deps in one command. No `requirements.txt`.

## Enterprise Architecture Patterns

This section maps enterprise orchestration concepts to Pixeltable primitives. Everything below is either already implemented in the starter kit or achievable by composing existing features.

### Orchestration Layer

The computed column chain IS the orchestration engine. `setup_pixeltable.py` defines the orchestration schema — inserting a row triggers the full DAG automatically. No Airflow, no Temporal, no explicit workflow engine.

### Memory Management

Two tiers are implemented:
- **Short-term (conversation-scoped)** — `_get_recent_chat_history(conversation_id)` retrieves recent turns from the current thread.
- **Long-term (semantic recall)** — `_search_chat_history(query_text)` searches across ALL past conversations by embedding similarity.

To add a **knowledge bank** (user preferences, facts, persistent notes), add another table with an embedding index and register its search query as a tool — see [agents-memory-mcp.md](https://github.com/pixeltable/pixeltable-skill/blob/main/references/agents-memory-mcp.md).

### Agent Discovery / Routing

The LLM chooses which tools to call based on the query — this IS agent discovery. The tool registry (`pxt.tools(web_search, _search_documents, _search_video_transcripts)`) maps directly to the "Agent Discovery" concept: matching task requirements to capabilities at runtime.

For explicit intent routing (classify → dispatch to specialized handlers), use a computed column:

```python
@pxt.udf
def route_prompt(intent: str, query: str) -> list[dict]:
    prompts = {
        "technical": "You are a senior technical support engineer.",
        "billing": "You are a billing specialist. Be empathetic.",
        "general": "You are a friendly customer service representative.",
    }
    system = prompts.get(intent.strip().lower(), prompts["general"])
    return [{"role": "system", "content": system}, {"role": "user", "content": query}]

agent.add_computed_column(
    intent=messages(model="...", messages=[...]).content[0].text,
    if_exists="ignore",
)
agent.add_computed_column(
    routed_messages=route_prompt(agent.intent, agent.prompt),
    if_exists="ignore",
)
```

### Multi-Agent / Orchestrator-Worker (A2A)

Pixeltable's `pxt.udf(table, return_value=...)` wraps an entire pipeline table as a callable function — this is the "AI Agents Marketplace" concept. Each worker table is a specialized agent:

```python
# Worker A: summarizer pipeline
summarizer = pxt.create_table("agents.summarizer", {"text": pxt.String}, ...)
summarizer.add_computed_column(summary=messages(...), ...)
summarize_fn = pxt.udf(summarizer, return_value=summarizer.summary)

# Worker B: fact-checker pipeline
checker = pxt.create_table("agents.checker", {"claim": pxt.String}, ...)
checker.add_computed_column(assessment=messages(...), ...)
fact_check_fn = pxt.udf(checker, return_value=checker.assessment)

# Orchestrator calls workers as computed columns (auto-parallelized)
orchestrator.add_computed_column(summary=summarize_fn(text=orchestrator.article), ...)
orchestrator.add_computed_column(fact_check=fact_check_fn(claim=orchestrator.article), ...)
```

Independent computed columns run in parallel automatically — no `asyncio.gather`, no explicit threading.

### MCP Protocol Integration

Connect to any MCP-compliant server to extend the agent with external tools:

```python
mcp_tools = pxt.mcp_udfs("http://localhost:8000/mcp")
tools = pxt.tools(web_search, _search_documents, *mcp_tools)
```

MCP tools are called via `invoke_tools()` exactly like local UDFs. See the commented block in `setup_pixeltable.py` and the [MCP Server repo](https://github.com/pixeltable/mcp-server-pixeltable-developer).

### Privacy & Security Guardrails

The starter kit implements:
- **Input validation** — length limits and sanitization in the `/api/agent/query` endpoint
- **CORS restrictions** — configurable origin allowlist (`config.CORS_ORIGINS`)
- **Container hardening** — non-root user, dropped capabilities in Helm deployment
- **Secrets management** — API keys via environment variables / K8s Secrets

For LLM-based guardrails (content filtering, prompt injection detection), add a computed column before the initial LLM call:

```python
agent.add_computed_column(
    safety_check=messages(
        model="...",
        messages=[{"role": "user", "content": "Is this safe? Reply SAFE or UNSAFE:\n\n" + agent.prompt}],
    ).content[0].text,
    if_exists="ignore",
)
```

### Response Personalization

The agent accepts per-request `temperature`, `max_tokens`, and `system_prompt` via the API. The frontend Settings panel exposes these controls. For deeper personalization (user profiles, personas), add a `personas` table and look up persona settings before insert — see how [Pixelbot](https://github.com/pixeltable/pixelbot) implements `user_personas`.

## Key Patterns to Follow

When extending this template:

**Adding a new data type:**
1. Add a table in `setup_pixeltable.py` with `pxt.create_table()`
2. Add views/iterators for processing (`create_view` + iterator)
3. Add embedding indexes for search (`add_embedding_index` with explicit `idx_name`)
4. In the router file, get table references with `pxt.get_table()` and define `@pxt.query` functions
5. Register routes in the same router file:
   - `add_insert_route` for uploads (`uploadfile_inputs` for media)
   - `add_delete_route` for deletion
   - `add_query_route` for each `@pxt.query`
6. Update the frontend `api.ts` to call the new endpoints

**Adding a computed column:**
```python
table.add_computed_column(
    new_col=some_function(table.existing_col),
    if_exists="ignore",
)
```

**Adding a new `@pxt.query` + route:**
```python
# In routers/my_router.py:
import pixeltable as pxt
from pixeltable.serving import FastAPIRouter
import config

router = FastAPIRouter(prefix="/api/my-stuff", tags=["my-stuff"])
my_table = pxt.get_table(f"{config.APP_NAMESPACE}.my_table")

@pxt.query
def list_my_items():
    return my_table.select(name=my_table.name, score=my_table.score)

router.add_query_route(path="/items", query=list_my_items, method="get")
```

**Insert with `return_rows=True` (get computed results without a follow-up query):**
```python
from models import AgentResult  # extra="ignore" to discard columns you don't need

status = table.insert([row], return_rows=True)
result = AgentResult.model_validate(status.rows[0])  # typed access to computed columns
```

**Adding a tool to the agent:**
1. Define the function with `@pxt.udf` or `@pxt.query`
2. Add it to the `pxt.tools()` call in `setup_pixeltable.py`
3. Re-run `python setup_pixeltable.py`

## Files to Read First

If you're new to this codebase, read in this order:

1. `setup_pixeltable.py` — the core. Defines the entire data model and agent pipeline (no router queries).
2. `routers/data.py` — `FastAPIRouter` + co-located `@pxt.query` (shows `add_insert_route`, `add_delete_route`, `add_query_route`).
3. `routers/search.py` — `FastAPIRouter` + co-located `@pxt.query` (4 similarity search endpoints).
4. `routers/agent.py` — mixed: declarative routes + 1 hand-written endpoint (shows when you *must* keep custom code).
5. `functions.py` — `@pxt.udf` definitions used by the agent pipeline.
6. `frontend/src/lib/api.ts` + `types/index.ts` — how the frontend consumes PXT routes with client-side aggregation.
