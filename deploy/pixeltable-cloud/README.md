# Pixeltable Cloud — `pxt deploy`

Deploy your Pixeltable service directly to **Pixeltable Cloud** — same schema as `pxt serve`, no Dockerfile, no container management, no persistent volume setup.

```
pxt serve  → runs locally (same config, zero cloud setup)
pxt deploy → deploys to Pixeltable Cloud (managed)
```

## How It Works

`pxt deploy` reads `pixeltable.toml`, bundles your schema + table metadata + dependencies, builds a Docker image in the cloud, and deploys it to managed infrastructure. The service stays in sync with your schema — redeploying is the same command.

## Quick Start (local)

```bash
cd deploy/pixeltable-cloud
uv sync
PYTHONPATH=. pxt serve openai_demo
```

Test the endpoints locally:

```bash
# Image: returns a job_url (background job — gpt-4o-mini vision runs async)
curl -F "image=@examples/eagle_nebula_pillars.webp" http://localhost:8000/image
# → {"id":"...","job_url":"http://localhost:8000/jobs/..."}

# Poll until status == "done", then read result
curl http://localhost:8000/jobs/<job_id>
# → {"status":"done","result":{"description":"..."}}

# Document: synchronous — summary returned immediately
curl -X POST -H "Content-Type: application/json" \
     -d @examples/article.json \
     http://localhost:8000/document
# → {"summary":"..."}
```

OpenAPI docs at [http://localhost:8000/docs](http://localhost:8000/docs).

## Deploy to Pixeltable Cloud

### 1. Create an environment

```bash
pxt environment create --org <your-org> --cpus 1 --memory-gb 1 dev
```

### 2. Add secrets

```bash
pxt environment add-secret --org <your-org> dev OPENAI_API_KEY $OPENAI_API_KEY
```

### 3. Deploy (2 workers)

```bash
pxt deploy openai_demo --org <your-org>
```

The CLI bundles your project, builds a Docker image in CI, and starts the service. When it finishes it prints:

```
Service 'openai_demo' is live at: https://dev.pxt.run/<org>/dev/openai_demo
```

### 4. Test the live endpoint

```bash
export PXT_ENDPOINT=https://dev.pxt.run/<org>/dev/openai_demo

# Image (background job)
curl -H "X-api-key: $PIXELTABLE_API_KEY" \
     -F "image=@examples/lagoon_nebula.jpg" \
     $PXT_ENDPOINT/image
# → {"id":"...","job_url":"https://.../jobs/..."}

# Poll for result
curl -H "X-api-key: $PIXELTABLE_API_KEY" \
     $PXT_ENDPOINT/jobs/<job_id>
# → {"status":"done","result":{"description":"..."}}

# Document (synchronous)
curl -H "X-api-key: $PIXELTABLE_API_KEY" \
     -H "Content-Type: application/json" \
     -d @examples/article.json \
     $PXT_ENDPOINT/document
# → {"summary":"..."}
```

### 5. Scale to 3 workers

Edit `pixeltable.toml` and change `workers = 2` to `workers = 3` in the `[[deployment]]` block:

```toml
[[deployment]]
name    = "openai_demo"
service = "openai_demo"
env     = "dev"
workers = 3
```

Redeploy:

```bash
pxt deploy openai_demo --org <your-org>
```

The service updates in place — no downtime, 3 replicas now serving traffic.

### 6. Stop / start / delete

```bash
# Stop (scale to zero — keeps the service, no traffic)
pxt service stop --org <your-org> openai_demo

# Start it back up
pxt service start --org <your-org> openai_demo

# Delete the service and tear down the environment
# Note: stop the service first — delete will fail if it is still running
pxt service stop --org <your-org> openai_demo
pxt service delete --org <your-org> openai_demo
pxt environment delete --org <your-org> dev
```

## Architecture

```
POST /image   ──►  pipeline.images table  (background job → returns job_url)
                     image (input)
                     description ──►  gpt-4o-mini vision (one sentence)
GET  /jobs/:id ──►  poll until status == "done", then read result

POST /document ──►  pipeline.documents table  (synchronous)
                      body (input)
                      summary    ──►  gpt-4o-mini (one sentence)
```

Both routes use `type = "compute"` — data flows through Pixeltable's computed column graph and results are returned without requiring persistent client-side storage.

## What Changes vs. `serving/`

| Concern | `serving/` (self-hosted) | `deploy/pixeltable-cloud/` (managed) |
|---|---|---|
| **Route type** | `insert` (persistent, query-able) | `compute` (stateless result) |
| **Storage** | Persistent volume + embedding indexes | Managed by Pixeltable |
| **Schema** | `schema.py` | `app.py` (same pattern) |
| **Dockerfile** | Required | Not needed |
| **Scaling** | Manual (container replicas) | `workers = N` in `pixeltable.toml` |

## See Also

- [`serving/`](../../serving/) — Declarative serving with `pxt serve` (insert routes, embedding search)
- [`orchestration/`](../../orchestration/) — Ephemeral batch processing with `export_sql`
- [`deploy/aws-cdk/`](../aws-cdk/) — Self-hosted ECS Fargate with persistent EFS volume
