# AWS ECS Fargate

Run the Pixeltable batch pipeline as an ECS Fargate task — serverless containers with Spot pricing (~70% cheaper). Trigger from SQS, EventBridge, or Step Functions.

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

## Spot Pricing

Use `FARGATE_SPOT` capacity provider for ~70% cost reduction. Tasks may be interrupted, but the pipeline is idempotent — re-run safely on retry.

```bash
aws ecs run-task \
  --capacity-provider-strategy capacityProvider=FARGATE_SPOT,weight=1 \
  ...
```
