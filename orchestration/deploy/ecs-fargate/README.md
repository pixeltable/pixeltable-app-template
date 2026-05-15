# AWS ECS Fargate

Run the Pixeltable batch pipeline as an ECS Fargate task. Serverless containers with Spot pricing (~70% cheaper). Trigger from SQS, EventBridge, or Step Functions.

## Prerequisites

- [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- An ECR repository and ECS cluster
- IAM roles for task execution and secrets access

## Files

| File | What it does |
|---|---|
| `task-definition.json` | Fargate task definition (2 vCPU, 4 GiB) |
| `eventbridge-rule.json` | EventBridge rule to trigger from SQS |

## Deploy

```bash
# 1. Create ECR repo and push image
aws ecr create-repository --repository-name pixeltable-pipeline
cd orchestration
docker build -t pixeltable-pipeline:latest .

aws ecr get-login-password | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
docker tag pixeltable-pipeline:latest ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/pixeltable-pipeline:latest
docker push ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/pixeltable-pipeline:latest

# 2. Store secrets
aws secretsmanager create-secret --name pixeltable/serving-db-url \
  --secret-string 'postgresql+psycopg://user:pass@host/db'
aws secretsmanager create-secret --name pixeltable/openai-api-key \
  --secret-string 'sk-...'

# 3. Register task definition (edit ACCOUNT_ID in task-definition.json first)
aws ecs register-task-definition --cli-input-json file://task-definition.json

# 4. Run the task
aws ecs run-task \
  --cluster your-cluster \
  --task-definition pixeltable-pipeline \
  --launch-type FARGATE \
  --capacity-provider-strategy capacityProvider=FARGATE_SPOT,weight=1 \
  --network-configuration '{
    "awsvpcConfiguration": {
      "subnets": ["subnet-xxx"],
      "securityGroups": ["sg-xxx"],
      "assignPublicIp": "ENABLED"
    }
  }'
```

## Trigger from SQS via EventBridge Pipes

```bash
aws pipes create-pipe \
  --name pixeltable-sqs-to-ecs \
  --source arn:aws:sqs:us-east-1:ACCOUNT_ID:pixeltable-batches \
  --target arn:aws:ecs:us-east-1:ACCOUNT_ID:cluster/your-cluster \
  --target-parameters '{
    "EcsTaskParameters": {
      "TaskDefinitionArn": "arn:aws:ecs:us-east-1:ACCOUNT_ID:task-definition/pixeltable-pipeline",
      "LaunchType": "FARGATE",
      "NetworkConfiguration": {
        "AwsvpcConfiguration": {
          "Subnets": ["subnet-xxx"],
          "AssignPublicIp": "ENABLED"
        }
      }
    }
  }' \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/pipes-execution-role
```

## Trigger from Webhook

ECS tasks can't receive HTTP directly. Use API Gateway to accept the webhook, then route to ECS via EventBridge or a Lambda proxy.

### Option 1: API Gateway -> EventBridge -> ECS RunTask

EventBridge can start an ECS task directly from an API Gateway request, no Lambda needed:

```bash
# 1. Create an EventBridge API Destination (for logging/tracing)
# 2. Create an HTTP API with EventBridge integration
API_ID=$(aws apigatewayv2 create-api \
  --name pixeltable-webhook \
  --protocol-type HTTP \
  --query ApiId --output text)

# 3. Create an EventBridge rule that starts the ECS task
aws events put-rule --name pixeltable-webhook-rule \
  --event-pattern '{
    "source": ["apigateway"],
    "detail-type": ["webhook"]
  }'

aws events put-targets --rule pixeltable-webhook-rule \
  --targets '[{
    "Id": "ecs-target",
    "Arn": "arn:aws:ecs:us-east-1:ACCOUNT_ID:cluster/your-cluster",
    "RoleArn": "arn:aws:iam::ACCOUNT_ID:role/eventbridge-ecs-role",
    "EcsParameters": {
      "TaskDefinitionArn": "arn:aws:ecs:us-east-1:ACCOUNT_ID:task-definition/pixeltable-pipeline",
      "LaunchType": "FARGATE",
      "NetworkConfiguration": {
        "awsvpcConfiguration": {
          "Subnets": ["subnet-xxx"],
          "AssignPublicIp": "ENABLED"
        }
      }
    }
  }]'
```

### Option 2: API Gateway -> Lambda -> ECS RunTask

If you need to validate the webhook payload or pass data to the task, use a small Lambda function as glue:

```bash
# Lambda that starts an ECS task (Python snippet)
# import boto3
# ecs = boto3.client("ecs")
# def handler(event, context):
#     ecs.run_task(
#         cluster="your-cluster",
#         taskDefinition="pixeltable-pipeline",
#         launchType="FARGATE",
#         networkConfiguration={...},
#         overrides={"containerOverrides": [{
#             "name": "pixeltable-pipeline",
#             "environment": [{"name": "INPUT_SOURCE", "value": event["body"]}]
#         }]}
#     )

aws lambda create-function \
  --function-name pixeltable-webhook-trigger \
  --runtime python3.12 --handler index.handler \
  --role arn:aws:iam::ACCOUNT_ID:role/lambda-ecs-trigger-role \
  --zip-file fileb://webhook_trigger.zip

# Attach API Gateway
aws apigatewayv2 create-api \
  --name pixeltable-webhook \
  --protocol-type HTTP \
  --target arn:aws:lambda:us-east-1:ACCOUNT_ID:function:pixeltable-webhook-trigger
```

Option 2 is more flexible: you can validate signatures, transform the payload, and pass environment variable overrides to the ECS task.

## Spot Pricing

Use `FARGATE_SPOT` capacity provider for ~70% cost reduction. Tasks may be interrupted, but the pipeline is idempotent. Re-run safely on retry.

```bash
aws ecs run-task \
  --capacity-provider-strategy capacityProvider=FARGATE_SPOT,weight=1 \
  ...
```
