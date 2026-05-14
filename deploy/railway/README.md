# Railway — Pixeltable Starter Kit

Deploy the Pixeltable Starter Kit on [Railway](https://railway.app). Includes a [`railway.json`](https://docs.railway.com/reference/config-as-code) config for build settings and health checks.

## Prerequisites

- Railway account
- Repo pushed to GitHub

## Quick Start

### Option 1: Dashboard deploy

1. Go to [railway.app/new](https://railway.app/new)
2. Select **Deploy from GitHub repo** and connect your repo
3. In your service → **Settings** → **Config as Code**, set the config file path to `/deploy/railway/railway.json`
4. Redeploy to pick up the config

No need to copy files to the repo root — Railway supports [custom config file paths](https://docs.railway.com/guides/config-as-code#using-a-custom-config-as-code-file).

### Option 2: Railway CLI

```bash
npm i -g @railway/cli
railway login
railway init
railway up
```

Then set the config file path in the dashboard as described above.

### Set environment variables

In the Railway dashboard → your service → **Variables**:

```
PIXELTABLE_HOME=/data/pixeltable
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### Add persistent storage

In the Railway dashboard → your service → **Volumes**:
1. Click **New Volume**
2. Mount path: `/data/pixeltable`
3. Size: 10 GB (or more)

## Configuration

The `railway.json` configures build (Dockerfile) and deploy settings (health check, restart policy). Everything else is set in the Railway dashboard.

| Setting | Where | Description |
|---|---|---|
| Build/deploy | `railway.json` | Dockerfile builder, health check, restart policy |
| Env vars | Dashboard → Variables | API keys, Pixeltable config |
| Volume | Dashboard → Volumes | Persistent storage at `/data/pixeltable` |
| Region | Dashboard → Settings | Deploy region |
| Scaling | Dashboard → Settings | Vertical (RAM/CPU) and horizontal (replicas) |

### Optional environment variables

```
PIXELTABLE_INPUT_MEDIA_DEST=s3://your-bucket/input    # external media storage
PIXELTABLE_OUTPUT_MEDIA_DEST=s3://your-bucket/output
```

## Persistent Storage

Railway Volumes provide persistent NVMe storage. Mount at `/data/pixeltable` to persist Pixeltable's embedded Postgres and file cache across deploys.

**Important:** Each Railway service replica needs its own volume. For multi-replica setups, configure external Postgres and set `PIXELTABLE_DB`.

## Custom Domain

In the Railway dashboard → your service → **Settings** → **Domains**, add a custom domain or use the generated `*.up.railway.app` URL.

## Troubleshooting

- **Performance issues:** The default Railway configuration allocates minimum resources. If your app has high load, increase memory and CPU in Settings → Resources.
- **Running out of disk space:** The default volume is small. Increase it in the Railway dashboard for large media workloads.
- **First deploy is slow:** Schema init downloads embedding models (~500 MB) on first run. Subsequent deploys reuse the cached models from the persistent volume.
