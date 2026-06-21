# Deployment Guide

Deploy the **backend pattern** (FastAPI + Pixeltable) from this monorepo. Batch and serving patterns have their own deploy configs — see [`batch/deploy/`](../batch/deploy/) and [`serving/deploy/`](../serving/deploy/).

## Storage

All options below should set `PIXELTABLE_HOME=/data/pixeltable` to a persistent volume. For large media workloads:

```bash
PIXELTABLE_INPUT_MEDIA_DEST=s3://your-bucket/input    # or gs:// or az://
PIXELTABLE_OUTPUT_MEDIA_DEST=s3://your-bucket/output
```

See [Pixeltable Configuration](https://docs.pixeltable.com/platform/configuration.md).

## Docker Compose

Local or single-server deployment:

```bash
cp .env.example .env          # add API keys
docker compose up --build     # http://localhost:8000
```

Pixeltable data persists via named Docker volumes: `pixeltable-data` (catalog + blobs at `/data/pixeltable`) and `uploads` (raw files at `/app/data`). To reset: `docker compose down -v`.

## Platform Quick Reference

| Platform | Quick start | Details |
|----------|-------------|---------|
| **Fly.io** | `cp deploy/fly/fly.toml .` → `fly launch` → create volume → set secrets → `fly deploy` | [`fly/README.md`](fly/README.md) |
| **Render** | `cp deploy/render/render.yaml .` → push → Blueprint Instance in dashboard | [`render/README.md`](render/README.md) |
| **Railway** | Deploy from GitHub; config path `/deploy/railway/railway.json`; volume at `/data/pixeltable` | [`railway/README.md`](railway/README.md) |
| **DigitalOcean** | `doctl apps create --spec deploy/digitalocean/app.yaml` | [`digitalocean/README.md`](digitalocean/README.md) |
| **Vercel** | Frontend only — `cp deploy/vercel/vercel.json frontend/` → `npx vercel` | [`vercel/README.md`](vercel/README.md) |
| **Helm** | Build/push image → `helm install pixeltable-starter ./deploy/helm/pixeltable-starter` | [`helm/README.md`](helm/README.md) |
| **Terraform** | `cd deploy/terraform-{k8s,gke,aks}` → `terraform apply` | [`terraform-k8s/README.md`](terraform-k8s/README.md) |
| **AWS CDK** | `cd deploy/aws-cdk && pip install -r requirements.txt && cdk deploy` | [`aws-cdk/README.md`](aws-cdk/README.md) |

### Fly.io

```bash
cp deploy/fly/fly.toml .
fly launch --no-deploy
fly volumes create pxt_data --size 10 --region iad
fly secrets set OPENAI_API_KEY=sk-... ANTHROPIC_API_KEY=sk-ant-...
fly deploy
```

### Render

```bash
cp deploy/render/render.yaml .
git add render.yaml && git commit -m "add render blueprint" && git push
# Then: Render dashboard → New → Blueprint Instance → connect repo
```

### Railway

1. [railway.app/new](https://railway.app/new) → **Deploy from GitHub repo**
2. Service → **Settings** → set config path to `/deploy/railway/railway.json`
3. Set `PIXELTABLE_HOME=/data/pixeltable`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` in Variables
4. Add a Volume mounted at `/data/pixeltable`

### DigitalOcean

```bash
doctl apps create --spec deploy/digitalocean/app.yaml
```

App Platform doesn't have native persistent volumes. See [`digitalocean/README.md`](digitalocean/README.md) for persistence options.

### Vercel (frontend only)

```bash
cp deploy/vercel/vercel.json frontend/
cd frontend && npx vercel --yes
# Set BACKEND_URL=https://your-backend.fly.dev in Vercel dashboard
```

Deploys the React frontend on Vercel's edge CDN with `/api` proxied to your backend.

### Helm (any existing Kubernetes cluster)

```bash
docker build -t <your-registry>/pixeltable-starter:latest .
docker push <your-registry>/pixeltable-starter:latest
helm install pixeltable-starter ./deploy/helm/pixeltable-starter \
  --set image.repository=<your-registry>/pixeltable-starter \
  --set secrets.OPENAI_API_KEY=sk-... \
  --set secrets.ANTHROPIC_API_KEY=sk-ant-...
```

**Local testing with [minikube](https://minikube.sigs.k8s.io/docs/start/):**

```bash
minikube start --cpus=4 --memory=6144
docker build -t pixeltable-starter:latest .
minikube image load pixeltable-starter:latest
helm install pixeltable-starter ./deploy/helm/pixeltable-starter \
  --set image.pullPolicy=Never --set service.type=NodePort \
  --set secrets.OPENAI_API_KEY=$OPENAI_API_KEY \
  --set secrets.ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY
kubectl port-forward svc/pixeltable-starter 9000:8000
```

### Terraform (provision cluster from scratch)

```bash
cd deploy/terraform-k8s && terraform init && terraform apply   # AWS EKS
cd deploy/terraform-gke && terraform init && terraform apply   # GCP GKE
cd deploy/terraform-aks && terraform init && terraform apply   # Azure AKS
```

Each creates a managed K8s cluster with a 50Gi persistent volume.

### AWS CDK (ECS Fargate)

```bash
cd deploy/aws-cdk && pip install -r requirements.txt && cdk deploy
```

Serverless containers with EFS for persistent storage and ALB for load balancing.

## Batch processing deploy

For cron jobs, queue workers, and event-driven pipelines (no HTTP server):

| Platform | Config | Best for |
|----------|--------|----------|
| [Cloud Run Jobs](../batch/deploy/cloud-run/) | `cloudbuild.yaml` | GCP, cron/Pub/Sub triggers |
| [Kubernetes Job](../batch/deploy/k8s-job/) | `job.yaml`, `cronjob.yaml` | Any K8s, queue-driven scaling |
| [ECS Fargate](../batch/deploy/ecs-fargate/) | `task-definition.json` | AWS Spot pricing |
| [Lambda](../batch/deploy/lambda/) | `Dockerfile`, `handler.py` | Small batches, up to 15 min |

See [`batch/README.md`](../batch/README.md) for details.
