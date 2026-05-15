# Google Cloud Run Jobs

Run the Pixeltable batch pipeline as a [Cloud Run Job](https://cloud.google.com/run/docs/create-jobs). No HTTP server, scale-to-zero billing, up to 24h runtime per task.

## Prerequisites

- [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) (`gcloud`)
- A GCP project with billing enabled
- Docker (for local builds) or Cloud Build (no Docker needed)

## Deploy

```bash
# 1. Set your project
export PROJECT_ID=your-gcp-project
export REGION=us-central1
gcloud config set project $PROJECT_ID

# 2. Enable APIs
gcloud services enable \
  artifactregistry.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com

# 3. Create Artifact Registry repo (once)
gcloud artifacts repositories create pixeltable \
  --repository-format=docker --location=$REGION

# 4. Build and push (choose one)

# Option A: Cloud Build (no local Docker needed)
gcloud builds submit batch/ \
  --tag $REGION-docker.pkg.dev/$PROJECT_ID/pixeltable/pipeline:latest \
  --region $REGION

# Option B: Local Docker build
cd batch
docker build -t $REGION-docker.pkg.dev/$PROJECT_ID/pixeltable/pipeline:latest .
docker push $REGION-docker.pkg.dev/$PROJECT_ID/pixeltable/pipeline:latest

# 5. Create the job
gcloud run jobs create pixeltable-pipeline \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/pixeltable/pipeline:latest \
  --region $REGION \
  --memory 4Gi --cpu 2 \
  --task-timeout 3600s \
  --max-retries 3 \
  --set-env-vars PIXELTABLE_HOME=/tmp/pixeltable \
  --set-env-vars SERVING_DB_URL=postgresql+psycopg://user:pass@host/db

# 6. Run it
gcloud run jobs execute pixeltable-pipeline --region $REGION
```

> **Permissions:** Cloud Build needs `roles/artifactregistry.writer` and `roles/storage.admin` on the default Compute Engine service account (`PROJECT_NUMBER-compute@developer.gserviceaccount.com`). If the build succeeds but push fails with "Permission denied", grant these roles.

## Trigger on a Schedule

```bash
# Run daily at 2 AM UTC
gcloud scheduler jobs create http pixeltable-daily \
  --schedule "0 2 * * *" \
  --uri "https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/pixeltable-pipeline:run" \
  --http-method POST \
  --oauth-service-account-email $PROJECT_ID-compute@developer.gserviceaccount.com \
  --location $REGION
```

## Trigger from Pub/Sub

Use [Eventarc](https://cloud.google.com/run/docs/triggering/pubsub-push) to trigger the job when a message arrives:

```bash
gcloud eventarc triggers create pixeltable-pubsub-trigger \
  --location $REGION \
  --destination-run-service pixeltable-pipeline \
  --destination-run-region $REGION \
  --event-filters "type=google.cloud.pubsub.topic.v1.messagePublished" \
  --transport-topic projects/$PROJECT_ID/topics/batch-requests
```

## Trigger from Webhook

Cloud Run Jobs can't receive HTTP directly (they're not services). The standard pattern is: webhook -> Pub/Sub -> Eventarc -> Job. This reuses the Pub/Sub trigger you already set up above.

### Option 1: Webhook -> Pub/Sub (recommended)

Point the webhook source at a Pub/Sub push endpoint. Any HTTP POST publishes a message, which triggers the job via Eventarc.

```bash
# 1. Create a Pub/Sub topic (if not done already)
gcloud pubsub topics create batch-requests

# 2. Set up Eventarc trigger (same as "Trigger from Pub/Sub" above)
gcloud eventarc triggers create pixeltable-pubsub-trigger \
  --location $REGION \
  --destination-run-service pixeltable-pipeline \
  --destination-run-region $REGION \
  --event-filters "type=google.cloud.pubsub.topic.v1.messagePublished" \
  --transport-topic projects/$PROJECT_ID/topics/batch-requests

# 3. Send a webhook payload (from any HTTP client or external service)
curl -X POST \
  "https://pubsub.googleapis.com/v1/projects/$PROJECT_ID/topics/batch-requests:publish" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"data": "'$(echo -n '{"title":"New doc","body":"Content"}' | base64)'"}]}'
```

### Option 2: Cloud Function as webhook receiver

For external webhooks (GitHub, Stripe, etc.) that POST to a fixed URL, deploy a small Cloud Function that validates the payload and triggers the job:

```bash
# Deploy a lightweight function that calls the Jobs API
gcloud functions deploy pixeltable-webhook \
  --gen2 --runtime python312 --region $REGION \
  --entry-point handle_webhook \
  --trigger-http --allow-unauthenticated \
  --set-env-vars PROJECT_ID=$PROJECT_ID,REGION=$REGION,JOB_NAME=pixeltable-pipeline \
  --source - <<'PYEOF'
import functions_framework
from google.cloud import run_v2
import os

@functions_framework.http
def handle_webhook(request):
    client = run_v2.JobsClient()
    job_name = f"projects/{os.environ['PROJECT_ID']}/locations/{os.environ['REGION']}/jobs/{os.environ['JOB_NAME']}"
    operation = client.run_job(name=job_name)
    return {"status": "triggered", "operation": operation.name}, 200
PYEOF
```

The function URL becomes your webhook endpoint. Add signature validation for production use.

## Custom Input

Pass arguments via the `--args` flag or override the entrypoint:

```bash
# Process a specific JSON file from GCS
gcloud run jobs update pixeltable-pipeline \
  --args="--input,/data/batch.json" \
  --region $REGION

# Or override entirely via environment variable
gcloud run jobs update pixeltable-pipeline \
  --set-env-vars INPUT_SOURCE=gs://your-bucket/batch.json \
  --region $REGION
```

## Limits

| Resource | Limit |
|---|---|
| Runtime | Up to 24 hours per task |
| CPU | Up to 8 vCPU |
| Memory | Up to 32 GiB |
| Retries | Configurable (default 3) |
| Parallelism | Up to 100 tasks per execution |
| Billing | Per-second, only during execution |
