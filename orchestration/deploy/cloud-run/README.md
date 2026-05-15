# Google Cloud Run Jobs

Run the Pixeltable batch pipeline as a [Cloud Run Job](https://cloud.google.com/run/docs/create-jobs). No HTTP server, scale-to-zero billing, up to 24h runtime per task.

## Prerequisites

- [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) (`gcloud`)
- A GCP project with Artifact Registry and Cloud Run APIs enabled
- Docker (for building the image)

## Deploy

```bash
# 1. Set your project
export PROJECT_ID=your-gcp-project
export REGION=us-central1
gcloud config set project $PROJECT_ID

# 2. Enable APIs
gcloud services enable \
  artifactregistry.googleapis.com \
  run.googleapis.com

# 3. Create Artifact Registry repo (once)
gcloud artifacts repositories create pixeltable \
  --repository-format=docker --location=$REGION

# 4. Build and push
cd orchestration
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
