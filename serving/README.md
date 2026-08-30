# Pixeltable serving

One application file declares tables, computed columns, indexes, and HTTP routes.
`pxt schema update` applies the tables. `pxt service` serves the `FastAPIRouter`
in the same file.

This is the default `uvx pixeltable-new myapp` pattern. Python 3.11+.
No HTTP: use [`batch/`](../batch/).

```
app.py                         CLI
TableModel + FastAPIRouter     pxt schema update app.py pipeline
                               catalog directory `pipeline`
                               (not a folder on disk)
                               pxt service update app.py pipeline
                               pxt service run app.py pipeline
```

`pixeltable.toml` is the project root. Schema and service refuse a file with no
root. `pxt init` writes one if you copied files by hand.

## Quick start

```bash
cd serving
uv sync
uv run pxt schema update app.py pipeline
uv run pxt service update app.py pipeline
uv run pxt service list
```

Foreground on port 8000:

```bash
uv run pxt schema update app.py pipeline
uv run pxt service run app.py pipeline --port 8000
```

OpenAPI is at `/docs`. Docker: `docker compose up --build`.

### Test it

Use the URL from `pxt service list`, or `http://localhost:8000` after `service run`:

```bash
curl -X POST http://localhost:8000/api/ingest/document \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "body": "Pixeltable replaces the AI data stack.", "source_id": "api-001"}'

curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query_text": "data infrastructure"}'

curl http://localhost:8000/api/documents
curl http://localhost:8000/api/images
```

## Application file

An annotation is a stored column. An assignment is a computed column. Indexes
belong on the model (`__indexes__`).

`pipeline` is the catalog directory the models bind to.

```bash
pxt schema update app.py pipeline
pxt service update app.py pipeline
```

Hosted:

```bash
pxt db update pxt://org:db
pxt schema update app.py pxt://org:db
pxt service update app.py pxt://org:db
```

[`deploy/pixeltable-cloud/`](deploy/pixeltable-cloud/).

Already have FastAPI:

```python
from fastapi import FastAPI
from app import api  # FastAPIRouter next to the TableModel classes

app = FastAPI()
app.include_router(api)
```

Apply with `pxt schema update app.py pipeline` first. Call `pxt.get_table()`
inside custom handlers.

Pass `export_sql=SqlExport(...)` to `add_insert_route` when each successful
insert should also land in an external database.
[HTTP serving](https://docs.pixeltable.com/howto/deployment/serving).

## Endpoints

| Method | Path | Type |
|--------|------|------|
| `POST` | `/api/search` | query |
| `GET` | `/api/documents` | query |
| `GET` | `/api/images` | query |
| `POST` | `/api/ingest/document` | insert |
| `POST` | `/api/ingest/image` | insert |
| `POST` | `/api/delete/document` | delete |
| `POST` | `/api/delete/image` | delete |

## Files

```
serving/
├── app.py              TableModel, indexes, @pxt.query, FastAPIRouter
├── pixeltable.toml     Project root
├── pyproject.toml
├── Dockerfile
└── docker-compose.yml
```
