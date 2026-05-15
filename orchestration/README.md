# Pixeltable Batch Processing

Use Pixeltable as a **batch processing engine** — no HTTP server, no FastAPI, no endpoints. A Python script that ingests data, lets computed columns do the work, exports structured results to a serving database via [`export_sql`](https://docs.pixeltable.com/howto/cookbooks/data/data-export-sql), and routes generated media directly to a cloud bucket via the [`destination`](https://docs.pixeltable.com/sdk/latest/table) parameter. The container shuts down when done.

**When to use this pattern:**
- Long-running batch jobs (processing thousands of documents, hours of video)
- Background tasks triggered by a queue, cron, or webhook
- Sidecar to your existing stack — you already have a serving layer and just need processing
- You don't need an HTTP API at all

This is the complement to the [starter kit](../README.md) (interactive web app with FastAPI) and [`serving/`](../serving/) (declarative API via `pxt serve`). If you need an API, use those instead. If you just need to process data and export results, this is the right pattern.

```
Cron / Queue / Webhook
(Cloud Scheduler, SQS, Pub/Sub, EventBridge)
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

This pattern runs as a **job** (finite task), not a **service** (HTTP server). Every major cloud has first-class support for this.

### Google Cloud Run Jobs

```
Cloud Scheduler / Pub/Sub / Eventarc → Cloud Run Job
```

```bash
gcloud run jobs create pixeltable-pipeline \
  --image <your-registry>/pixeltable-pipeline:latest \
  --set-env-vars PIXELTABLE_HOME=/tmp/pixeltable \
  --set-env-vars SERVING_DB_URL=postgresql+psycopg://... \
  --memory 4Gi --cpu 2 --task-timeout 3600s --max-retries 3

gcloud run jobs execute pixeltable-pipeline
```

- Scale-to-zero billing (pay only during execution)
- Up to 24h runtime per task, 4 vCPU, 32 GiB RAM
- Trigger from Cloud Scheduler (cron), Pub/Sub, Eventarc, or Workflows

### ECS Fargate Spot + SQS

```
SQS Queue → EventBridge Rule → ECS Fargate Spot Task
```

- Pay only when processing (~70% cheaper with Spot)
- Scale to zero when idle
- Pass batch payload via environment variable or S3 pointer

### AWS Lambda (small batches)

```
S3 event / SQS message / EventBridge → Lambda
```

- Up to 15 min / 10 GiB — suitable for smaller batches
- Set `PIXELTABLE_HOME=/tmp/pixeltable`
- Package as a container image for larger dependencies

### Kubernetes Job + KEDA

```
Queue (SQS/Redis/Pub/Sub) → KEDA ScaledJob → K8s Job (Spot nodes)
```

### AWS Batch

- Submit jobs to a managed queue
- Auto-provisions optimal instance types
- Native Spot support with automatic retries

### Azure Container Apps Jobs

```
Azure Queue Storage / Service Bus → Container Apps Job
```

- Event-driven or scheduled execution
- Scale to zero, consumption billing

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
