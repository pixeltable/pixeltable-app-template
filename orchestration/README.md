# Pixeltable Ephemeral Orchestration

Use Pixeltable as an **ephemeral processing engine**: spin up a container, ingest text and media, let computed columns do the work, export structured results to a serving database via [`export_sql`](https://docs.pixeltable.com/howto/cookbooks/data/data-export-sql), and route generated media directly to a cloud bucket via the [`destination`](https://docs.pixeltable.com/sdk/v0.5.9/table) parameter. No persistent infrastructure — the container shuts down when done.

This is the complement to the [starter kit](../README.md) (long-running server) and [`serving/`](../serving/) (`pxt serve`). Here Pixeltable is a sidecar to your existing stack — it processes data and hands results back.

```
SQS / Cron / Webhook
        │
        ▼
  Ephemeral Container
  ┌──────────────────────────────────────────────────────┐
  │  1. Create schema (idempotent)                       │
  │  2. Insert text + media from queue/RDBMS/S3          │
  │  3. Computed columns process everything              │
  │     - Sentence chunking + embedding indexes          │
  │     - Image thumbnails + metadata extraction         │
  │     - Optional LLM summary (OpenAI)                  │
  │  4. export_sql → structured data to serving DB       │
  │  5. destination → generated media to cloud bucket    │
  │  6. Container exits                                  │
  └──────────────────────────────────────────────────────┘
        │                           │
        ▼                           ▼
  Your Serving DB              Your Cloud Bucket
  (Postgres/MySQL/Snowflake)   (S3/GCS/Azure)
```

## Quick Start

```bash
cd orchestration
uv sync
PIXELTABLE_HOME=/tmp/pxt uv run python pipeline.py
```

Output:

```
Using 5 sample documents
Inserting documents...
Inserted 22 rows with 0 errors in 3.1 s
Inserting images...
Inserted 2 rows with 0 errors in 0.4 s
Exporting results...
  Documents -> sqlite:///serving.db:processed_documents
  Images    -> sqlite:///serving.db:processed_images

  Serving DB — processed_documents (5 rows):
    doc-001  Introduction to Pixeltable
    doc-002  Computed Columns
    ...

  Search test — 'how does Pixeltable handle orchestration?' (3 hits):
    [0.71] This lets you use Pixeltable as a processing engine...
    [0.66] For batch workloads, Pixeltable can run in an ephemeral container...

Pipeline completed in 3.3s
```

### Docker

```bash
docker compose up --build    # runs pipeline, exports to volume, exits
```

### Custom input

```bash
uv run python pipeline.py --input batch.json
uv run python pipeline.py --input-db 'postgresql://user:pass@host/db'
```

## How It Works

### Schema as code (`schema.py`)

One file defines the entire data model. Importing it creates everything:

- **Documents pipeline:** `pipeline.documents` table → `pipeline.sentences` view (sentence-level chunking via `string_splitter`) → embedding index for semantic search
- **Images pipeline:** `pipeline.images` table → thumbnail (128×128 b64), width, height, mode (all computed automatically)
- **Optional:** LLM summary column when `OPENAI_API_KEY` is set

### Two output paths

| Output type | Method | Where it goes |
|---|---|---|
| **Structured data** (text, numbers, JSON) | `export_sql` | Serving RDBMS (Postgres, MySQL, Snowflake, etc.) |
| **Generated media** (thumbnails, audio, etc.) | `destination` parameter | Cloud bucket (S3, GCS, Azure Blob) |

### Batch export via `export_sql`

```python
from pixeltable.io.sql import export_sql

export_sql(
    docs.select(docs.source_id, docs.title, docs.body),
    "processed_documents",
    db_connect_str="postgresql+psycopg://user:pass@host/db",
    if_exists="replace",
)
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `PIXELTABLE_HOME` | `~/.pixeltable` | Set to `/tmp/pixeltable` for ephemeral |
| `SERVING_DB_URL` | `sqlite:///serving.db` | SQLAlchemy connection string for export target |
| `OPENAI_API_KEY` | — | Enables LLM summary column |
| `MEDIA_DEST` | — | Cloud URI for generated media (e.g. `s3://bucket/out`) |

## Production Deployment

### ECS Fargate Spot + SQS (cheapest)

```
SQS Queue → EventBridge Rule → ECS Fargate Spot Task
```

- Pay only when processing (~70% cheaper with Spot)
- Scale to zero when idle
- Pass batch payload via environment variable or S3 pointer

### Kubernetes Job + KEDA

```
Queue (SQS/Redis) → KEDA ScaledJob → K8s Job (Spot nodes)
```

### AWS Batch

- Submit jobs to a managed queue
- Auto-provisions optimal instance types
- Native Spot support with automatic retries

## See Also

- **[`serving/`](../serving/)** — Declarative API serving with `pxt serve` (zero Python web code)
- **[`backend/`](../backend/)** — Full backend with FastAPI routers + React frontend

## Files

```
orchestration/
├── schema.py           Tables, views, embedding indexes, computed columns
├── pipeline.py         Batch ingest → compute → export_sql → exit
├── sample_batch.json   Example JSON input
├── pyproject.toml      Dependencies (uv)
├── Dockerfile          Ephemeral container (PIXELTABLE_HOME=/tmp)
└── docker-compose.yml  Local testing
```
