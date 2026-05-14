# Fly.io — Pixeltable Starter Kit

Deploy the Pixeltable Starter Kit on [Fly.io](https://fly.io) with persistent volumes and auto-scaling.

## Prerequisites

- [flyctl CLI](https://fly.io/docs/flyctl/install/)
- Fly.io account

## Quick Start

```bash
# Copy fly.toml to repo root
cp deploy/fly/fly.toml .

# Create app (don't deploy yet — we need a volume first)
fly launch --no-deploy

# Create persistent volume for Pixeltable data
fly volumes create pxt_data --size 10 --region iad

# Set API keys (stored as encrypted secrets, not in fly.toml)
fly secrets set \
  OPENAI_API_KEY=sk-... \
  ANTHROPIC_API_KEY=sk-ant-...

# Deploy
fly deploy
```

The app will be available at `https://<app-name>.fly.dev`. First deploy takes ~3 min (schema init + model downloads). Check progress with `fly logs`.

## Configuration

Edit `fly.toml` before deploying:

| Setting | Default | Description |
|---|---|---|
| `primary_region` | `iad` | Fly.io region (see `fly platform regions`) |
| `vm.memory` | `4gb` | RAM per machine (Pixeltable + embedded Postgres) |
| `vm.cpus` | `2` | vCPUs |
| `mounts.source` | `pxt_data` | Volume name for persistent storage |
| `auto_stop_machines` | `stop` | Scale to zero when idle (saves cost) |

### Environment variables

```bash
fly secrets set OPENAI_API_KEY=sk-...
fly secrets set ANTHROPIC_API_KEY=sk-ant-...

# Optional: external media storage
fly secrets set PIXELTABLE_INPUT_MEDIA_DEST=s3://your-bucket/input
fly secrets set PIXELTABLE_OUTPUT_MEDIA_DEST=s3://your-bucket/output
```

## Persistent Storage

Pixeltable's embedded Postgres and file cache live on a Fly volume mounted at `/data/pixeltable`. Volumes survive deploys and machine restarts. To resize:

```bash
fly volumes extend <volume-id> --size 50
```

**Important:** Fly volumes are pinned to a single region and machine. For multi-region or high availability, configure external Postgres and set `PIXELTABLE_DB` accordingly.

## Scaling

```bash
fly scale count 2          # run 2 machines (each needs its own volume)
fly scale memory 8192      # 8 GB RAM per machine
```

## Logs and SSH

```bash
fly logs                   # stream logs
fly ssh console            # SSH into the machine
```
