# Kubernetes Job

Run the Pixeltable batch pipeline as a Kubernetes Job — one-shot or scheduled via CronJob. For queue-driven scaling, add [KEDA](https://keda.sh/).

## Files

| File | What it does |
|---|---|
| `job.yaml` | One-shot Job + Secret |
| `cronjob.yaml` | Scheduled daily at 2 AM UTC |
| `keda-scaledjob.yaml` | Queue-driven: one Job per message (requires KEDA) |

## Deploy (one-shot)

```bash
# Build and load image
docker build -t pixeltable-pipeline:latest ../../
kubectl apply -f job.yaml

# Watch it run
kubectl logs -f job/pixeltable-pipeline

# Check status
kubectl get jobs
```

## Deploy (scheduled)

```bash
kubectl apply -f cronjob.yaml
kubectl get cronjobs
```

## Deploy (queue-driven with KEDA)

```bash
# Install KEDA (once)
helm repo add kedacore https://kedacore.github.io/charts
helm install keda kedacore/keda --namespace keda --create-namespace

# Deploy the ScaledJob
kubectl apply -f keda-scaledjob.yaml
```

Edit `keda-scaledjob.yaml` to match your queue type (SQS, Redis, Pub/Sub, RabbitMQ — see [KEDA scalers](https://keda.sh/docs/scalers/)).

## Test with minikube

```bash
minikube start --cpus=4 --memory=4096
docker build -t pixeltable-pipeline:latest ../../
minikube image load pixeltable-pipeline:latest

# Update secret with your DB URL (or leave default sqlite for testing)
kubectl apply -f job.yaml
kubectl logs -f job/pixeltable-pipeline
```

## Configuration

Set secrets before deploying:

```bash
kubectl create secret generic pixeltable-pipeline-secrets \
  --from-literal=serving-db-url='postgresql+psycopg://user:pass@host/db' \
  --from-literal=openai-api-key='sk-...'
```

Or edit the `stringData` section in `job.yaml`.
