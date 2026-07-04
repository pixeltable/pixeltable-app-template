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
| `handler.py` | Lambda entry point: parses SQS / API Gateway events, runs pipeline |

## Deploy

```bash
# 1. Build the Lambda container image
cd batch
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

## Trigger from Webhook

Lambda is the most natural webhook receiver: no separate HTTP server needed. Use a Function URL (simplest) or API Gateway (more control).

### Function URL (zero config)

```bash
# Add a public HTTPS endpoint directly to the function
aws lambda create-function-url-config \
  --function-name pixeltable-pipeline \
  --auth-type NONE

# Returns something like:
#   https://abc123xyz.lambda-url.us-east-1.on.aws/
```

POST documents directly to the URL:

```bash
curl -X POST https://abc123xyz.lambda-url.us-east-1.on.aws/ \
  -H "Content-Type: application/json" \
  -d '{"documents": [{"title": "New doc", "body": "Content to process"}]}'
```

For authenticated webhooks, use `--auth-type AWS_IAM` and sign requests, or validate a shared secret in the handler.

### API Gateway (custom domain, auth, throttling)

```bash
# Create HTTP API (v2, simpler than REST API)
API_ID=$(aws apigatewayv2 create-api \
  --name pixeltable-webhook \
  --protocol-type HTTP \
  --target arn:aws:lambda:us-east-1:ACCOUNT_ID:function:pixeltable-pipeline \
  --query ApiId --output text)

echo "Webhook URL: https://$API_ID.execute-api.us-east-1.amazonaws.com/"
```

API Gateway adds rate limiting, custom domains, API keys, and request validation. Use this when the webhook source (GitHub, Stripe, etc.) sends high volumes or you need access control.

### Webhook payload format

The handler accepts any JSON POST body. Wrap documents in a `documents` array, or send a single document object:

```json
{"documents": [{"title": "Doc 1", "body": "..."}, {"title": "Doc 2", "body": "..."}]}
```

```json
{"title": "Single doc", "body": "Content here"}
```

## Trigger on Schedule

```bash
# Run every hour
aws events put-rule --name pixeltable-hourly --schedule-expression 'rate(1 hour)'
aws events put-targets --rule pixeltable-hourly \
  --targets Id=1,Arn=arn:aws:lambda:us-east-1:ACCOUNT_ID:function:pixeltable-pipeline
```
