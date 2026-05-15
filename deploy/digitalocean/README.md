# DigitalOcean App Platform: Pixeltable Starter Kit

Deploy the Pixeltable Starter Kit on [DigitalOcean App Platform](https://www.digitalocean.com/products/app-platform) using the included app spec.

## Prerequisites

- [DigitalOcean account](https://cloud.digitalocean.com/registrations/new)
- Repo pushed to GitHub
- Optional: [doctl CLI](https://docs.digitalocean.com/reference/doctl/how-to/install/)

## Quick Start

### Option 1: Dashboard

1. Go to [cloud.digitalocean.com/apps](https://cloud.digitalocean.com/apps) → **Create App**
2. Select **GitHub** as the source, connect your repo
3. DigitalOcean auto-detects the Dockerfile
4. In **Resources**, select **Professional** plan (4 GB RAM minimum for embeddings + Postgres)
5. In **Environment Variables**, add:
   - `PIXELTABLE_HOME=/data/pixeltable`
   - `OPENAI_API_KEY` (encrypt)
   - `ANTHROPIC_API_KEY` (encrypt)
6. Deploy

### Option 2: doctl CLI

```bash
doctl apps create --spec deploy/digitalocean/app.yaml
```

Then set the secret env vars in the dashboard (secrets can't be set via the spec file).

### Set up persistent storage

DigitalOcean App Platform doesn't natively support persistent volumes for Docker-based services. For persistent Pixeltable data, use one of these approaches:

**Option A: DigitalOcean Managed Database (recommended for production)**

Use an external Postgres database instead of Pixeltable's embedded one:

```bash
# Create a managed Postgres cluster
doctl databases create pixeltable-db --engine pg --size db-s-1vcpu-1gb --region nyc1

# Set the connection string as an env var
# Dashboard → App → Environment Variables:
PIXELTABLE_DB=postgresql://user:pass@host:25060/defaultdb?sslmode=require
```

**Option B: Use a Droplet instead**

For the simplest persistent setup, deploy to a [DigitalOcean Droplet](https://www.digitalocean.com/products/droplets) with Docker:

```bash
# On your Droplet:
git clone https://github.com/pixeltable/pixeltable-starter-kit.git
cd pixeltable-starter-kit
cp .env.example .env   # add API keys
docker compose up -d
```

This gives you persistent block storage at `/data/pixeltable`.

## Configuration

| Setting | Default | Description |
|---|---|---|
| `instance_size_slug` | `professional-s` | 2 vCPU, 4 GB RAM (minimum recommended) |
| `instance_count` | `1` | Number of containers |
| `region` | `nyc` | DigitalOcean region (`nyc`, `sfo`, `ams`, `sgp`, etc.) |

### Instance sizes

| Slug | vCPUs | RAM | $/month |
|---|---|---|---|
| `professional-s` | 2 | 4 GB | ~$24 |
| `professional-m` | 4 | 8 GB | ~$48 |
| `professional-l` | 8 | 16 GB | ~$96 |

### Optional environment variables

```
PIXELTABLE_INPUT_MEDIA_DEST=s3://your-bucket/input
PIXELTABLE_OUTPUT_MEDIA_DEST=s3://your-bucket/output
CORS_ORIGINS=https://your-frontend.vercel.app
```

DigitalOcean Spaces (S3-compatible) works with Pixeltable's media destination config.

## Custom Domain

In the App dashboard → **Settings** → **Domains**, add your custom domain. DigitalOcean provides free SSL.

## See Also

- [`deploy/fly/`](../fly/): Fly.io (persistent volumes, scale-to-zero)
- [`deploy/render/`](../render/): Render (persistent disk included)
- [`deploy/railway/`](../railway/): Railway (NVMe volumes)
