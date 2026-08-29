# Pixeltable batch

No HTTP. Apply the application file, insert, let computed columns run, export, exit.

```bash
cd batch
uv sync
uv run pxt schema update app.py pipeline
PIXELTABLE_HOME=/tmp/pxt uv run python pipeline.py
```

`pipeline.py` also calls `TableModel.update_all('pipeline')`, so a job can run
that file as its only command. `pixeltable.toml` is the project root. Python 3.11+.

Need an API: [`serving/`](../serving/).

Custom input: `uv run python pipeline.py --input my_batch.json`.

Docker: `docker compose up --build`.

## Schema

`TableModel` classes in `app.py`. Apply with `pxt schema update app.py pipeline`.

Structured export: `export_sql` to a serving database. Generated media:
`destination=` on a column when routing to a cloud bucket.

```python
from pixeltable.io.sql import export_sql

export_sql(
    docs.select(docs.source_id, docs.title, docs.body),
    "processed_documents",
    db_connect_str="postgresql+psycopg://user:pass@host/db",
    if_exists="replace",
)
```

| Variable | Default |
|---|---|
| `PIXELTABLE_HOME` | `~/.pixeltable` (use `/tmp/pixeltable` for ephemeral) |
| `SERVING_DB_URL` | `sqlite:///serving.db` |
| `MEDIA_DEST` | unset |

## Files

```
batch/
├── app.py
├── pixeltable.toml
├── pipeline.py
├── sample_batch.json
├── pyproject.toml
├── Dockerfile
└── docker-compose.yml
```
