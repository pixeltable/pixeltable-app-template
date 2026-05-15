# Render: Pixeltable Starter Kit

Deploy the Pixeltable Starter Kit on [Render](https://render.com) using a Blueprint (Infrastructure as Code).

## Prerequisites

- Render account
- Repo pushed to GitHub or GitLab

## Quick Start

### Option 1: Blueprint (recommended)

```bash
# Copy render.yaml to repo root
cp deploy/render/render.yaml .
git add render.yaml && git commit -m "add render blueprint" && git push
```

Then in the Render dashboard:
1. **New** → **Blueprint Instance**
2. Connect your repo
3. Set `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` in the env vars prompt (marked `sync: false`)
4. Click **Apply**

Subsequent deploys reattach to the same disk: Pixeltable data persists across deploys.

### Option 2: Manual setup

1. **New** → **Web Service**
2. Connect your repo, select **Docker** runtime
3. Set environment variables:
   - `PIXELTABLE_HOME=/data/pixeltable`
   - `OPENAI_API_KEY=sk-...`
   - `ANTHROPIC_API_KEY=sk-ant-...`
4. Add a **Disk**: mount path `/data/pixeltable`, size 10 GB
5. Deploy

## Configuration

Edit `render.yaml` before deploying:

| Setting | Default | Description |
|---|---|---|
| `plan` | `standard` | Render plan (`starter`, `standard`, `pro`): standard recommended for 4 GB RAM |
| `region` | `oregon` | Deploy region |
| `disk.sizeGB` | `10` | Persistent disk for Pixeltable data |

### Environment variables

Set in the Render dashboard or `render.yaml`:

```yaml
envVars:
  - key: OPENAI_API_KEY
    sync: false           # prompts for value on deploy
  - key: ANTHROPIC_API_KEY
    sync: false
  - key: PIXELTABLE_INPUT_MEDIA_DEST
    value: s3://your-bucket/input    # optional: external media
```

## Persistent Storage

Render Disks provide persistent block storage mounted at `/data/pixeltable`. Data survives deploys and restarts. Disks are included in Standard and above plans.

## Custom Domain

```bash
# In Render dashboard → Settings → Custom Domains
# Or via render.yaml:
customDomains:
  - name: pixeltable.yourdomain.com
```
