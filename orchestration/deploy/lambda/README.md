# AWS Lambda (Container Image)

Run the Pixeltable batch pipeline as an AWS Lambda function using a container image. Best for smaller batches that complete within 15 minutes.

## Limits

| Resource | Limit |
|---|---|
| Runtime | 15 minutes max |
| Memory | Up to 10 GiB |
| Storage (`/tmp`) | 10 GiB |
| Payload | 6 MB sync, 256 KB async |

For longer-running jobs, use [Cloud Run Jobs](../cloud-run/), [ECS Fargate](../ecs-fargate/), or [Kubernetes Jobs](../k8s-job/) instead.

## Files

| File | What it does |
|---|---|
| `Dockerfile` | Lambda container image (based on AWS Lambda Python 3.12 base) |
| `handler.py` | Lambda entry point: parses SQS/S3 events, runs pipeline |

## Deploy

```bash
# 1. Build the Lambda container image
cd orchestration
docker build -f deploy/lambda/Dockerfile -t pixeltable-pipeline-lambda:latest .

# 2. Push to ECR
aws ecr create-repository --repository-name pixeltable-pipeline-lambda
aws ecr get-login-password | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
docker tag pixeltable-pipeline-lambda:latest ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/pixeltable-pipeline-lambda:latest
docker push ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/pixeltable-pipeline-lambda:latest

# 3. Create the function
aws lambda create-function \
  --function-name pixeltable-pipeline \
  --package-type Image \
  --code ImageUri=ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/pixeltable-pipeline-lambda:latest \
  --role arn:aws:iam::ACCOUNT_ID:role/lambda-execution-role \
  --timeout 900 \
  --memory-size 4096 \
  --environment 'Variables={PIXELTABLE_HOME=/tmp/pixeltable,SERVING_DB_URL=postgresql+psycopg://user:pass@host/db}'

# 4. Test it
aws lambda invoke --function-name pixeltable-pipeline output.json
cat output.json
```

## Trigger from SQS

```bash
aws lambda create-event-source-mapping \
  --function-name pixeltable-pipeline \
  --event-source-arn arn:aws:sqs:us-east-1:ACCOUNT_ID:pixeltable-batches \
  --batch-size 10 \
  --maximum-batching-window-in-seconds 60
```

## Trigger on Schedule

```bash
# Run every hour
aws events put-rule --name pixeltable-hourly --schedule-expression 'rate(1 hour)'
aws events put-targets --rule pixeltable-hourly \
  --targets Id=1,Arn=arn:aws:lambda:us-east-1:ACCOUNT_ID:function:pixeltable-pipeline
```
