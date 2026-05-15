# Pixeltable Cloud (`pxt deploy`)

> **Coming soon.** `pxt deploy` is being built in [pixeltable/pixeltable#1319](https://github.com/pixeltable/pixeltable/pull/1319) and [#1331](https://github.com/pixeltable/pixeltable/pull/1331). The CLI command exists but cloud hosting is not yet available.

Deploy your Pixeltable service directly to **Pixeltable Cloud**. Same config as `pxt serve`, no Dockerfile, no container management, no persistent volume setup.

## How It Works

`pxt deploy` reads the same `[[tool.pixeltable.service]]` config from `pyproject.toml` that `pxt serve` uses, bundles your schema + table metadata + dependencies, and deploys to managed infrastructure.

```
pxt serve  → runs locally (or in your own container)
pxt deploy → deploys to Pixeltable Cloud (managed)
```

The `serving/` directory in this repo is already configured for both. The same `schema.py` and `pyproject.toml` work with either command.

## What Changes vs. Self-Hosted

| Concern | Self-hosted (`pxt serve`) | Pixeltable Cloud (`pxt deploy`) |
|---|---|---|
| **Compute** | Your container (Fly/Render/Railway/K8s) | Managed by Pixeltable |
| **Storage** | Persistent volume at `PIXELTABLE_HOME` | Managed by Pixeltable |
| **Schema** | Same `schema.py` | Same `schema.py` |
| **Routes** | Same `[tool.pixeltable.service]` config | Same config |
| **Dockerfile** | Required | Not needed |
| **Scaling** | Manual (replicas, instance size) | Auto-scaling |

## Usage (when available)

```bash
cd serving

# Local development (works today)
PYTHONPATH=. pxt serve pipeline

# Deploy to Pixeltable Cloud (coming soon)
pxt deploy prod
```

### Configuration

Add a deployment environment to your `pyproject.toml`:

```toml
# Service config (same as pxt serve, already in serving/pyproject.toml)
[[tool.pixeltable.service]]
name = "pipeline"
prefix = "/api"
modules = ["schema"]
# ... routes ...

# Deployment environment (for pxt deploy)
[[tool.pixeltable.deployment]]
name = "prod"
services = ["pipeline"]
```

The deployment config references the service by name. Services can also be defined in code via `module:attr` references to a `FastAPI` app instance ([PR #1331](https://github.com/pixeltable/pixeltable/pull/1331)).

## Why This Matters

Today you have two paths for serving Pixeltable:

1. **Full backend** (`backend/`): hand-written FastAPI + React, deployed to any platform
2. **Declarative serving** (`serving/`): `pxt serve` with TOML config, deployed to Fly/Render/Railway/K8s

`pxt deploy` adds a third:

3. **Managed cloud**: same declarative config, zero infrastructure. One command.

All three use the same schema pattern. Moving from `pxt serve` (self-hosted) to `pxt deploy` (managed) requires only adding the deployment block to your config. No code changes.

## See Also

- [`serving/`](../../serving/): Declarative serving with `pxt serve` (works today)
- [PR #1319](https://github.com/pixeltable/pixeltable/pull/1319): `pxt deploy` CLI + deployment environments
- [PR #1331](https://github.com/pixeltable/pixeltable/pull/1331): Code-defined services (`module:attr`)
