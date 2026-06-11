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

This example shows the full org → cluster → environment → deploy flow: one org secret shared by both environments, with dev carrying an optional override.

### 1. Create a cluster

A cluster is the compute pool that environments run on. One cluster can serve multiple environments (dev, prod).

```bash
pxt cluster create main --org <your-org> \
    --instance t3.small \
    --max-nodes 5 \
    --region us-east-1
```

### 2. Add an org-level secret

Org secrets are inherited by all environments in the org. Store your OpenAI key here once — both dev and prod will receive it automatically.

```bash
pxt org add-secret --org <your-org> OPENAI_API_KEY $OPENAI_API_KEY
```

### 3. Create environments pointing to the cluster

```bash
pxt environment create dev  --org <your-org> --cluster main
pxt environment create prod --org <your-org> --cluster main
```

### 4. (Optional) Override the API key for dev

Env-level secrets shadow the org-level secret for that env only. Use a different OpenAI project key in dev to keep dev and prod quotas separate:

```bash
pxt environment add-secret --org <your-org> dev OPENAI_API_KEY $OPENAI_API_KEY_DEV
```

Prod continues to use the org-level key. Dev uses the env-level override.

### 5. Deploy

```bash
# Deploy to dev (1 worker)
pxt deploy openai_demo_dev --org <your-org>

# Deploy to prod (3 workers)
pxt deploy openai_demo_prod --org <your-org>
```

The CLI bundles your project, builds a Docker image in CI, and starts the service. When it finishes:

```
Service 'openai_demo' is live at: https://dev.pxt.run/<org>/dev/openai_demo
Service 'openai_demo' is live at: https://dev.pxt.run/<org>/prod/openai_demo
```

### 6. Test the live endpoints

```bash
export DEV_ENDPOINT=https://dev.pxt.run/<org>/dev/openai_demo
export PROD_ENDPOINT=https://dev.pxt.run/<org>/prod/openai_demo

# Image (background job)
curl -H "X-api-key: $PIXELTABLE_API_KEY" \
     -F "image=@examples/eagle_nebula_pillars.webp" \
     $DEV_ENDPOINT/image
# → {"id":"...","job_url":"https://.../jobs/..."}

# Poll for result
curl -H "X-api-key: $PIXELTABLE_API_KEY" \
     $DEV_ENDPOINT/jobs/<job_id>
# → {"status":"done","result":{"description":"..."}}

# Document (synchronous)
curl -H "X-api-key: $PIXELTABLE_API_KEY" \
     -H "Content-Type: application/json" \
     -d @examples/article.json \
     $PROD_ENDPOINT/document
# → {"summary":"..."}
```

### 7. Inspect secrets and cluster

```bash
# List org-level secrets
pxt org list-secrets --org <your-org>

# List env-level secrets (shows only keys, not values)
pxt environment list-secrets --org <your-org> dev
pxt environment list-secrets --org <your-org> prod

# List clusters
pxt cluster list --org <your-org>

# Get cluster details
pxt cluster get main --org <your-org>
```

### 8. Scale and redeploy

Edit `pixeltable.toml` and change `workers` in the `[[deployment]]` block, then redeploy:

```bash
pxt deploy openai_demo_prod --org <your-org>
```

The service updates in place — no downtime, new replica count serving traffic.

### 9. Tear down

```bash
# Stop services first, then delete
pxt service stop --org <your-org> openai_demo
pxt service delete --org <your-org> openai_demo

# Delete environments
pxt environment delete --org <your-org> dev
pxt environment delete --org <your-org> prod

# Remove org secret
pxt org remove-secret --org <your-org> OPENAI_API_KEY

# Delete cluster
pxt cluster delete --org <your-org> main
```

## Secret Resolution Order

When a service starts, secrets are resolved in this order (later wins):

1. Org-level secrets (`pxt org add-secret`)
2. Environment-level secrets (`pxt environment add-secret`) — shadow org secrets for that env

This means you can set `OPENAI_API_KEY` once at the org level and override it per-environment as needed.

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
| **Secrets** | Environment variables | Org + env secrets via `pxt org/environment` |

## See Also

- [`serving/`](../../serving/) — Declarative serving with `pxt serve` (insert routes, embedding search)
- [`orchestration/`](../../orchestration/) — Ephemeral batch processing with `export_sql`
- [`deploy/aws-cdk/`](../aws-cdk/) — Self-hosted ECS Fargate with persistent EFS volume
