# Kubernetes Job

Run the Pixeltable batch pipeline as a Kubernetes Job: one-shot or scheduled via CronJob. For queue-driven scaling, add [KEDA](https://keda.sh/).

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

Edit `keda-scaledjob.yaml` to match your queue type (SQS, Redis, Pub/Sub, RabbitMQ). See [KEDA scalers](https://keda.sh/docs/scalers/).

## Trigger from Webhook

Kubernetes Jobs can't listen for HTTP. The two standard patterns: push webhooks into a queue (and let KEDA scale Jobs from it), or deploy a lightweight webhook receiver that creates Jobs on demand.

### Option 1: Webhook -> Queue -> KEDA ScaledJob (recommended)

This reuses the KEDA setup from above. Point your webhook source at any HTTP-to-queue bridge (most message brokers have one), and KEDA handles the rest.

For example, with SQS:

```bash
# External service sends webhook to SQS via AWS API or an HTTP proxy
# KEDA ScaledJob (keda-scaledjob.yaml) picks it up automatically
kubectl apply -f keda-scaledjob.yaml
```

With Redis Streams or RabbitMQ, use the corresponding [KEDA scaler](https://keda.sh/docs/scalers/).

### Option 2: Webhook receiver Deployment

Deploy a minimal service that creates Kubernetes Jobs from incoming webhooks. This runs as a long-lived Deployment with a Service/Ingress.

```yaml
# webhook-receiver.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pixeltable-webhook
spec:
  replicas: 1
  selector:
    matchLabels:
      app: pixeltable-webhook
  template:
    metadata:
      labels:
        app: pixeltable-webhook
    spec:
      serviceAccountName: job-creator  # needs create/get permissions on batch/v1 Jobs
      containers:
        - name: receiver
          image: bitnami/kubectl:latest
          command: ["/bin/sh", "-c"]
          args:
            - |
              apk add --no-cache python3 py3-flask &&
              python3 -c "
              from flask import Flask, request
              import subprocess, json, uuid
              app = Flask(__name__)
              @app.route('/webhook', methods=['POST'])
              def webhook():
                  job_id = f'pixeltable-pipeline-{uuid.uuid4().hex[:8]}'
                  subprocess.run(['kubectl', 'create', 'job', job_id,
                                  '--from=cronjob/pixeltable-pipeline'], check=True)
                  return {'job': job_id}, 201
              app.run(host='0.0.0.0', port=8080)
              "
          ports:
            - containerPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: pixeltable-webhook
spec:
  selector:
    app: pixeltable-webhook
  ports:
    - port: 80
      targetPort: 8080
```

In practice, replace the inline script with a proper container image. The key idea: `kubectl create job --from=cronjob/pixeltable-pipeline` creates a one-off Job from an existing CronJob template.

```bash
kubectl apply -f webhook-receiver.yaml

# Test it
curl -X POST http://pixeltable-webhook/webhook \
  -H "Content-Type: application/json" \
  -d '{"source": "github", "event": "push"}'
```

Expose via Ingress or LoadBalancer for external webhooks.

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
