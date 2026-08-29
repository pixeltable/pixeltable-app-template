# Pixeltable Batch Processing

Use Pixeltable as a **batch processing engine**: no HTTP server, no FastAPI, no endpoints. A Python script that ingests data, lets computed columns do the work, exports structured results to a serving database via [`export_sql`](https://docs.pixeltable.com/howto/cookbooks/data/data-export-sql), and routes generated media directly to a cloud bucket via the [`destination`](https://docs.pixeltable.com/sdk/latest/table) parameter. The container shuts down when done.

**When to use this pattern:**
- Long-running batch jobs (processing thousands of documents, hours of video)
- Background tasks triggered by a queue, cron, or webhook
- Sidecar to your existing stack: you already have a serving layer and just need processing
- You don't need an HTTP API at all

This is the complement to the [starter kit](../README.md) (interactive web app with FastAPI) and [`serving/`](../serving/) (application file + `pxt service`). If you need an API, use those instead. If you just need to process data and export results, this is the right pattern.

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
cd batch
uv sync
uv run pxt schema update app.py pipeline
PIXELTABLE_HOME=/tmp/pxt uv run python pipeline.py
```

`pipeline.py` also calls `TableModel.update_all('pipeline')`, so a job can run that file as its only command. `pixeltable.toml` is the project root. Python 3.11+.

Output:

```
Loaded sample_batch.json
Inserting 5 documents...
Inserting 2 images...
Exporting...
  Documents -> sqlite:///serving.db:processed_documents
  Images    -> sqlite:///serving.db:processed_images

  Search: 'how does Pixeltable handle orchestration?' (3 hits)
    [0.71] This lets you use Pixeltable as a processing engine...
    [0.66] For batch workloads, Pixeltable can run in an ephemeral container...

Done in 3.3s
```

### Docker

```bash
docker compose up --build    # runs pipeline, exports to volume, exits
```

### Custom input

```bash
uv run python pipeline.py --input my_batch.json
```

## How It Works

### Schema as code (`app.py`)

`TableModel` classes declare the data model. Apply with `pxt schema update app.py pipeline`.

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
| `MEDIA_DEST` | | Cloud URI for generated media (e.g. `s3://bucket/out`). Add `destination=` on a `pxt.Column` in `app.py` when routing generated media to cloud storage. |

## Production Deployment

This pattern runs as a **job** (finite task), not a **service** (HTTP server). Every major cloud has first-class support for this. Ready-to-use configs live in `deploy/`:

| Platform | Config | Runtime | Triggers | Best for |
|---|---|---|---|---|
| [**Google Cloud Run Jobs**](deploy/cloud-run/) | `cloudbuild.yaml` | Up to 24h, 8 vCPU, 32 GiB | Cron, Pub/Sub, webhook (via Cloud Function) | GCP users |
| [**Kubernetes Job**](deploy/k8s-job/) | `job.yaml`, `cronjob.yaml`, `keda-scaledjob.yaml` | Unlimited | CronJob, queue (KEDA), webhook (via receiver) | Any K8s cluster |
| [**AWS ECS Fargate**](deploy/ecs-fargate/) | `task-definition.json` | Unlimited | SQS, EventBridge, webhook (via API Gateway) | AWS users, Spot (~70% cheaper) |
| [**AWS Lambda**](deploy/lambda/) | `Dockerfile`, `handler.py` | Up to 15 min, 10 GiB | SQS, schedule, **webhook (native Function URL)** | Small batches, event-driven |
| **AWS Batch** | (use ECS task def) | Unlimited | SQS, schedule | Managed queue, auto instance selection |
| **Azure Container Apps Jobs** | (use K8s Job pattern) | Unlimited | Queue, schedule | Azure, consumption billing |

Each folder has a README with full deploy commands. Quick summary:

### Google Cloud Run Jobs

```bash
# Build remotely with Cloud Build (no local Docker needed)
gcloud builds submit batch/ \
  --tag $REGION-docker.pkg.dev/$PROJECT_ID/pixeltable/pipeline:latest \
  --region $REGION
gcloud run jobs create pixeltable-pipeline \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/pixeltable/pipeline:latest \
  --region $REGION \
  --memory 4Gi --cpu 2 --task-timeout 3600s --max-retries 3 \
  --set-env-vars PIXELTABLE_HOME=/tmp/pixeltable
gcloud run jobs execute pixeltable-pipeline --region $REGION
```

See [`deploy/cloud-run/`](deploy/cloud-run/) for CI/CD via Cloud Build, cron scheduling, and Pub/Sub triggers.

### Kubernetes Job

```bash
docker build -t pixeltable-pipeline:latest .
kubectl apply -f deploy/k8s-job/job.yaml        # one-shot
kubectl apply -f deploy/k8s-job/cronjob.yaml     # scheduled (daily)
kubectl apply -f deploy/k8s-job/keda-scaledjob.yaml  # queue-driven (requires KEDA)
```

See [`deploy/k8s-job/`](deploy/k8s-job/) for minikube testing and KEDA setup.

### AWS ECS Fargate

```bash
docker build -t pixeltable-pipeline:latest .
# Push to ECR, then:
aws ecs run-task --task-definition pixeltable-pipeline --launch-type FARGATE \
  --capacity-provider-strategy capacityProvider=FARGATE_SPOT,weight=1 ...
```

See [`deploy/ecs-fargate/`](deploy/ecs-fargate/) for task definition, secrets, and SQS triggers via EventBridge Pipes.

### AWS Lambda (small batches)

```bash
docker build -f deploy/lambda/Dockerfile -t pixeltable-pipeline-lambda:latest .
# Push to ECR, then:
aws lambda create-function --function-name pixeltable-pipeline \
  --package-type Image --timeout 900 --memory-size 4096 ...
```

See [`deploy/lambda/`](deploy/lambda/) for the handler, SQS event source mapping, and schedule triggers.

## See Also

- **[`serving/`](../serving/)**: Declarative API serving with `app.py` + `pxt service`
- **[`backend/`](../backend/)**: Full backend with FastAPI routers + React frontend

## Files

```
batch/
├── app.py                  TableModel classes, views, embedding indexes
├── pixeltable.toml         Project root
├── pipeline.py             Batch ingest → compute → export_sql → exit
├── sample_batch.json       Example JSON input
├── pyproject.toml          Dependencies (uv)
├── Dockerfile              Ephemeral container (PIXELTABLE_HOME=/tmp)
├── docker-compose.yml      Local testing
└── deploy/
    ├── cloud-run/           Google Cloud Run Job + Cloud Build CI
    │   ├── cloudbuild.yaml
    │   └── README.md
    ├── k8s-job/             Kubernetes Job, CronJob, KEDA ScaledJob
    │   ├── job.yaml
    │   ├── cronjob.yaml
    │   ├── keda-scaledjob.yaml
    │   └── README.md
    ├── ecs-fargate/         AWS ECS Fargate task definition
    │   ├── task-definition.json
    │   └── README.md
    └── lambda/              AWS Lambda container image
        ├── Dockerfile
        ├── handler.py
        └── README.md
```
