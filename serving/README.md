# Pixeltable Declarative Serving

Serve Pixeltable tables and queries as a REST API with **zero Python web code**. Define your schema in Python, your routes in TOML, and run `pxt serve`.

**When to use this pattern:**
- You need an API (clients will make HTTP requests)
- You want automatic CRUD + search endpoints without writing FastAPI code
- Insert routes should trigger computed columns and return results in real time

**When NOT to use this:** If your workload is batch processing (cron jobs, queue consumers, long-running data pipelines), you don't need an HTTP server. Use [`batch/`](../batch/) instead (pure Python script, no web framework).

This is the complement to the [starter kit](../README.md) (full custom backend with a frontend) and [`batch/`](../batch/) (batch processing with no HTTP server).

```
Schema (Python)          Routes (TOML)                    Runtime
┌─────────────┐    ┌──────────────────────────┐    ┌─────────────────┐
│ schema.py   │    │ pyproject.toml           │    │ pxt serve       │
│             │    │ [tool.pixeltable.service] │    │                 │
│ Tables      │───▶│ insert routes            │───▶│ FastAPI app     │
│ Views       │    │ query routes             │    │ auto-generated  │
│ Indexes     │    │ delete routes            │    │ OpenAPI docs    │
│ @pxt.query  │    │ export_sql               │    │ /docs           │
└─────────────┘    └──────────────────────────┘    └─────────────────┘
```

## Quick Start

```bash
cd serving
uv sync
uv run python schema.py              # initialize tables, views, indexes
uv run pxt serve pipeline
```

```
Starting Pixeltable service: pipeline
  Listening on http://localhost:8000
  API docs at http://localhost:8000/docs
  Routes: 7
```

### Test it

```bash
# Insert a document (triggers chunking + embeddings automatically)
curl -X POST http://localhost:8000/api/ingest/document \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "body": "Pixeltable replaces the AI data stack.", "source_id": "api-001"}'

# Semantic search
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query_text": "data infrastructure"}'

# List documents
curl http://localhost:8000/api/documents

# List images
curl http://localhost:8000/api/images
```

### Docker

```bash
docker compose up --build    # long-running service on :8000
```

## How It Works

### Schema as code (`schema.py`)

Same schema pattern as `batch/`. One file defines tables, views, computed columns, embedding indexes, and `@pxt.query` functions:

- **Documents:** table → sentence chunking view → embedding index → `search_documents` query
- **Images:** table → thumbnail + metadata computed columns → `list_images` query
- **Optional:** LLM summary column when `OPENAI_API_KEY` is set

### Declarative routes (`pyproject.toml`)

Routes live in `[tool.pixeltable]` inside `pyproject.toml` (standard Python convention, no extra config file):

```toml
[[tool.pixeltable.service]]
name = "pipeline"

[[tool.pixeltable.service.routes]]
type = "query"
path = "/search"
query = "schema:search_documents"       # module:attribute path to @pxt.query
method = "post"

[[tool.pixeltable.service.routes]]
type = "insert"
path = "/ingest/document"
table = "pipeline.documents"
inputs = ["title", "body", "source_id"]
outputs = ["uuid"]
```

`pxt serve` reads this config, resolves the query functions via `module:attribute` paths, and generates a complete FastAPI app with OpenAPI docs. You can also use a standalone `pixeltable.toml` file; Pixeltable checks both locations.

### Live SQL export on insert

Insert routes can auto-export to a serving DB on every request (no batch step needed):

```toml
[[tool.pixeltable.service.routes]]
type = "insert"
path = "/ingest/document"
table = "pipeline.documents"
inputs = ["title", "body", "source_id"]
outputs = ["uuid"]

[tool.pixeltable.service.routes.export_sql]
db_connect = "postgresql+psycopg://user:pass@host/db"
table = "processed_documents"
method = "insert"
```

Data flows in via API → computed columns process it → results land in your serving DB automatically.

## Endpoints

| Method | Path | Type | Description |
|--------|------|------|-------------|
| `POST` | `/api/search` | query | Semantic search over document sentences |
| `GET` | `/api/documents` | query | List all documents |
| `GET` | `/api/images` | query | List all images with metadata |
| `POST` | `/api/ingest/document` | insert | Insert document (triggers chunking + embeddings) |
| `POST` | `/api/ingest/image` | insert | Upload image (triggers thumbnail + metadata) |
| `POST` | `/api/delete/document` | delete | Delete a document |
| `POST` | `/api/delete/image` | delete | Delete an image |

## Configuration

| Variable | Default | Description |
|---|---|---|
| `PIXELTABLE_HOME` | `~/.pixeltable` | Persistent storage for Pixeltable data |
| `OPENAI_API_KEY` | | Enables LLM summary column |

## Three Deployment Paths

This starter kit demonstrates three ways to deploy Pixeltable:

| Pattern | Folder | When to use |
|---|---|---|
| **Full Backend** | [`backend/`](../backend/) | You need custom endpoints, a frontend, hand-written logic |
| **Batch Processing** | [`batch/`](../batch/) | Sidecar to your existing stack; batch ingest, `export_sql`, exit |
| **Declarative Serving** | `serving/` (this) | Zero-code API: schema + TOML config, `pxt serve` generates everything |

### Coming soon: `pxt deploy`

`pxt deploy` extends this pattern to managed infrastructure. Deploy your service config directly to Pixeltable Cloud with auto-scaling and zero container management. Same TOML config, same schema, no Dockerfile needed. The CLI command is already merged ([PR #1319](https://github.com/pixeltable/pixeltable/pull/1319), [PR #1331](https://github.com/pixeltable/pixeltable/pull/1331)); cloud hosting is coming soon. See [`deploy/pixeltable-cloud/`](deploy/pixeltable-cloud/) for details.

## Files

```
serving/
├── schema.py           Tables, views, indexes, @pxt.query functions
├── pyproject.toml      Dependencies + pxt serve config (routes, modules, export_sql)
├── Dockerfile          Long-running container
└── docker-compose.yml  Local testing
```
