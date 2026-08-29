# Pixeltable Declarative Serving

One application file declares tables, computed columns, indexes, and HTTP routes. `pxt schema update` applies the tables. `pxt service` serves the `FastAPIRouter` in the same file.

**When to use this pattern:**
- You need an API (clients will make HTTP requests)
- You want insert, query, and delete endpoints without writing FastAPI handlers
- Insert routes should trigger computed columns and return results in real time

**When not to use this:** If your workload is batch processing (cron jobs, queue consumers, long-running data pipelines), you do not need an HTTP server. Use [`batch/`](../batch/) instead.

This is the default `uvx pixeltable-new myapp` pattern. Python 3.11+.

```
app.py                         CLI
┌─────────────────────┐        pxt schema update app.py pipeline
│ TableModel classes  │──────▶ catalog directory `pipeline`
│ FastAPIRouter       │        (not a folder on disk)
│ @pxt.query          │
└─────────────────────┘        pxt service update app.py pipeline
                               pxt service run app.py pipeline
```

`pixeltable.toml` marks this directory as a Pixeltable project root. Schema and service commands refuse a file with no root (`pixeltable.toml`, or `pyproject.toml` with `[tool.pixeltable]`). `pxt init` writes a root if you copied files by hand.

## Quick Start

```bash
cd serving
uv sync
uv run pxt schema update app.py pipeline
uv run pxt service update app.py pipeline
uv run pxt service list
```

`pxt service update` starts the service in the background and assigns a port. `pxt service list` prints the URL.

For a foreground process on port 8000 (containers, a development loop):

```bash
uv run pxt schema update app.py pipeline
uv run pxt service run app.py pipeline --port 8000
```

OpenAPI docs are at `/docs` on the bound port.

### Test it

Use the URL from `pxt service list`, or `http://localhost:8000` if you used `pxt service run --port 8000`:

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
docker compose up --build    # schema update, then pxt service run on :8000
```

## How It Works

### Application file (`app.py`)

An annotation is a stored column. An assignment is a computed column. Indexes belong on the model (`__indexes__`), not `add_embedding_index()`.

- **Documents:** table → sentence view (`string_splitter`) → embedding index → `search_documents`
- **Images:** table → thumbnail + width/height/mode → `list_images`
- **Routes:** `FastAPIRouter(name='pipeline', prefix='/api')` with the insert, query, and delete paths below

`pipeline` is the catalog directory the models bind to. It is not a folder on disk.

```bash
pxt schema update app.py pipeline
pxt service update app.py pipeline
```

Hosted catalog (no local HTTP): `pxt schema update app.py pxt://org:db`. `pxt service` is local-only.

### Live SQL export on insert

Pass `export_sql=SqlExport(...)` to `add_insert_route` when each successful insert should also land in an external database. See [HTTP serving](https://docs.pixeltable.com/howto/deployment/serving).

## Endpoints

| Method | Path | Type | Description |
|--------|------|------|-------------|
| `POST` | `/api/search` | query | Semantic search over document sentences |
| `GET` | `/api/documents` | query | List all documents |
| `GET` | `/api/images` | query | List all images with metadata |
| `POST` | `/api/ingest/document` | insert | Insert document (triggers chunking + embeddings) |
| `POST` | `/api/ingest/image` | insert | Upload image (triggers thumbnail + metadata) |
| `POST` | `/api/delete/document` | delete | Delete a document by primary key (`uuid`) |
| `POST` | `/api/delete/image` | delete | Delete an image by primary key (`uuid`) |

## Configuration

| Variable | Default | Description |
|---|---|---|
| `PIXELTABLE_HOME` | `~/.pixeltable` | Persistent storage for Pixeltable data |
| `OPENAI_API_KEY` | | Optional: add an LLM summary computed column in `app.py` |

## Three Deployment Paths

| Pattern | Folder | When to use |
|---|---|---|
| **Full Backend** | [`backend/`](../backend/) | Custom endpoints and a frontend. Mount `FastAPIRouter` from the application file. |
| **Batch Processing** | [`batch/`](../batch/) | Sidecar to your existing stack: batch ingest, `export_sql`, exit |
| **Declarative Serving** | `serving/` (this) | Application file + `pxt service` |

Same file against Pixeltable Cloud: `pxt schema update app.py pxt://org:db`. See [`deploy/pixeltable-cloud/`](deploy/pixeltable-cloud/).

## Files

```
serving/
├── app.py              TableModel classes, indexes, @pxt.query, FastAPIRouter
├── pixeltable.toml     Project root
├── pyproject.toml      Dependencies
├── Dockerfile          Long-running container (schema update + service run)
└── docker-compose.yml  Local testing
```
