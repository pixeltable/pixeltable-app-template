# Pixeltable Cloud (`pxt deploy`)

> **Coming soon.** `pxt deploy` is being built in [pixeltable/pixeltable#1319](https://github.com/pixeltable/pixeltable/pull/1319) and [#1331](https://github.com/pixeltable/pixeltable/pull/1331). The CLI command exists but cloud hosting is not yet available.

Deploy your Pixeltable service directly to **Pixeltable Cloud**. Same config as `pxt serve`, no Dockerfile, no container management, no persistent volume setup.

```
pxt serve openai_demo      # local development (works today)
pxt deploy openai_demo     # deploy to Pixeltable Cloud (coming soon)
```

## Example Configuration

A single TOML file defines both the service (routes) and the deployment (infrastructure):

```toml
# pixeltable.toml (or [tool.pixeltable] in pyproject.toml)
#
# Local dev:   pxt serve openai_demo
# Deploy:      pxt deploy openai_demo

[[service]]
name    = "openai_demo"
modules = ["app"]

# Upload an image -> returns job_url; poll job to get description.
[[service.routes]]
type              = "compute"
table             = "pipeline.images"
path              = "/image"
uploadfile_inputs = ["image"]
outputs           = ["description"]
background        = true

# Submit text -> summary via gpt-4o-mini.
[[service.routes]]
type    = "compute"
table   = "pipeline.documents"
path    = "/document"
inputs  = ["body"]
outputs = ["summary"]

[[deployment]]
name    = "openai_demo"
service = "openai_demo"
env     = "dev"
workers = 3
exclude = ["__pycache__", "*.pyc", ".git", ".env", "*.egg-info", ".venv"]
```

### What each section does

**`[[service]]`** defines the API, identical to `pxt serve`:
- `modules` imports your schema (tables, computed columns, indexes)
- Each `[[service.routes]]` becomes a REST endpoint

**`[[service.routes]]`** with `type = "compute"` runs a table's computed column pipeline on the input and returns the result. Two patterns:
- **Sync** (`background` omitted): input in, output back in one request
- **Async** (`background = true`): returns a job URL; client polls for the result (heavy processing like image/video)

**`[[deployment]]`** adds infrastructure intent:
- `service` references which service to deploy
- `env` selects the target environment (dev/staging/prod)
- `workers` sets concurrency (the platform decides what this means)
- `exclude` replaces `.dockerignore` / `.gcloudignore`

## What Changes vs. Self-Hosted

| Concern | Self-hosted (`pxt serve` + Fly/Render/Railway) | Pixeltable Cloud (`pxt deploy`) |
|---|---|---|
| **What you write** | Dockerfile + platform config (fly.toml, render.yaml, ...) | TOML config only |
| **Compute** | Your container on your infra | Managed by Pixeltable |
| **Storage** | Persistent volume at `PIXELTABLE_HOME` | Managed by Pixeltable |
| **Secrets** | Platform-specific (`fly secrets set`, dashboard UI, ...) | `pxt deploy --secret KEY=value` |
| **Scaling** | Manual (replicas, instance size, auto-scale rules) | `workers = N` |
| **Schema** | Same `schema.py` | Same `schema.py` |
| **Routes** | Same `[[service.routes]]` config | Same config |

## Code-Defined Services

For developers who outgrow TOML routes and write a custom FastAPI app, `pxt deploy` also supports `module:attr` references ([PR #1331](https://github.com/pixeltable/pixeltable/pull/1331)):

```toml
[[deployment]]
name    = "my_app"
service = "main:app"       # references FastAPI instance in main.py
env     = "prod"
workers = 5
```

This bridges the gap between the declarative `pxt serve` pattern and a full custom backend.

## Developer Journey

1. Write `app.py` (schema: tables + computed columns)
2. Write TOML config (routes + deployment)
3. `pxt serve openai_demo` to develop locally
4. `pxt deploy openai_demo` when ready

No Dockerfile. No `fly.toml`. No `render.yaml`. No Terraform. No IAM permissions. No volume mounts. No health check config.

## See Also

- [`serving/`](../../): Declarative serving with `pxt serve` (works today)
- [PR #1319](https://github.com/pixeltable/pixeltable/pull/1319): `pxt deploy` CLI + deployment environments
- [PR #1331](https://github.com/pixeltable/pixeltable/pull/1331): Code-defined services (`module:attr`)
