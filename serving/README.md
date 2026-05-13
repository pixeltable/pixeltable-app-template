# Pixeltable Declarative Serving

Serve Pixeltable tables and queries as a REST API with **zero Python web code**. Define your schema in Python, your routes in TOML, and run `pxt serve`. Pixeltable generates the FastAPI app for you.

This is the complement to the [starter kit](../README.md) (full custom backend) and [`orchestration/`](../orchestration/) (ephemeral batch). Here Pixeltable IS the server — no hand-written endpoints, no routers, no Pydantic models.

```
Schema (Python)          Routes (TOML)           Runtime
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ schema.py   │    │ pixeltable.toml  │    │ pxt serve       │
│             │    │                  │    │                 │
│ Tables      │───▶│ insert routes    │───▶│ FastAPI app     │
│ Views       │    │ query routes     │    │ auto-generated  │
│ Indexes     │    │ delete routes    │    │ OpenAPI docs    │
│ @pxt.query  │    │ export_sql       │    │ /docs           │
└─────────────┘    └──────────────────┘    └─────────────────┘
```

## Quick Start

```bash
cd serving
uv sync
PYTHONPATH=. uv run pxt serve pipeline
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

Same schema pattern as `orchestration/` — one file defines tables, views, computed columns, embedding indexes, and `@pxt.query` functions:

- **Documents:** table → sentence chunking view → embedding index → `search_documents` query
- **Images:** table → thumbnail + metadata computed columns → `list_images` query
- **Optional:** LLM summary column when `OPENAI_API_KEY` is set

### Declarative routes (`pixeltable.toml`)

Routes are TOML, not Python:

```toml
[[service]]
name = "pipeline"
modules = ["schema"]       # imports schema.py on startup

[[service.routes]]
type = "query"
path = "/search"
query = "schema.search_documents"   # dotted path to @pxt.query
method = "post"

[[service.routes]]
type = "insert"
path = "/ingest/document"
table = "pipeline.documents"
inputs = ["title", "body", "source_id"]
outputs = ["uuid"]
```

`pxt serve` reads this config, imports the module, resolves the query functions, and generates a complete FastAPI app with OpenAPI docs.

### Live SQL export on insert

Insert routes can auto-export to a serving DB on every request — no batch step needed:

```toml
[[service.routes]]
type = "insert"
path = "/ingest/document"
table = "pipeline.documents"
inputs = ["title", "body", "source_id"]
outputs = ["uuid"]

[service.routes.export_sql]
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
| `PYTHONPATH` | — | Must include the directory containing `schema.py` |
| `OPENAI_API_KEY` | — | Enables LLM summary column |

## Three Deployment Paths

This starter kit demonstrates three ways to deploy Pixeltable:

| Pattern | Folder | When to use |
|---|---|---|
| **Full Backend** | [`backend/`](../backend/) | You need custom endpoints, a frontend, hand-written logic |
| **Ephemeral Orchestration** | [`orchestration/`](../orchestration/) | Sidecar to your existing stack — batch ingest → `export_sql` → exit |
| **Declarative Serving** | `serving/` (this) | Zero-code API — schema + TOML config, `pxt serve` generates everything |

### Coming soon: `pxt deploy`

`pxt deploy` will extend this pattern to managed infrastructure — deploy your service config directly to Pixeltable Cloud with compute routes, auto-scaling, and zero container management. Same TOML config, same schema, no Dockerfile needed.

## Files

```
serving/
├── schema.py           Tables, views, indexes, @pxt.query functions
├── pixeltable.toml     pxt serve config (routes, modules, export_sql)
├── pyproject.toml      Dependencies (uv)
├── Dockerfile          Long-running container
└── docker-compose.yml  Local testing
```
