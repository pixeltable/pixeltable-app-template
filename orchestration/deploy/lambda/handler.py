"""AWS Lambda handler for the Pixeltable batch pipeline.

Wraps pipeline.py for Lambda execution. Supports multiple trigger types:
  - SQS messages (batch of records)
  - S3 events (object created)
  - API Gateway / Function URL webhooks (POST with JSON body)
  - EventBridge schedules
  - Direct invocation

Environment:
    PIXELTABLE_HOME    Must be /tmp/pixeltable (Lambda's writable directory)
    SERVING_DB_URL     SQLAlchemy connection string for export target
    OPENAI_API_KEY     Optional, enables LLM summary column
"""

import json
import os

os.environ.setdefault("PIXELTABLE_HOME", "/tmp/pixeltable")


def _parse_documents(event):
    """Extract documents from any supported event format."""

    # API Gateway v2 (Function URL) or API Gateway v1 (REST API)
    if "requestContext" in event and ("http" in event.get("requestContext", {}) or "httpMethod" in event):
        body = event.get("body", "")
        if event.get("isBase64Encoded"):
            import base64
            body = base64.b64decode(body).decode()
        if isinstance(body, str):
            body = json.loads(body) if body else {}
        docs = body.get("documents", body if isinstance(body, list) else [body])
        return [d for d in docs if isinstance(d, dict) and ("title" in d or "body" in d)]

    # SQS records
    records = event.get("Records", [])
    if records and "body" in records[0]:
        documents = []
        for record in records:
            payload = json.loads(record["body"])
            if isinstance(payload, list):
                documents.extend(payload)
            elif isinstance(payload, dict):
                documents.append(payload)
        return documents

    # S3 event: return the bucket/key info for the caller to handle
    if records and "s3" in records[0].get("eventName", "").lower():
        return []

    return []


def _make_response(status_code, body):
    """Format response for both API Gateway and direct invocation."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def lambda_handler(event, context):
    from pipeline import export_results
    import schema

    documents = _parse_documents(event)

    if documents:
        schema.documents.insert(documents)
    else:
        from pipeline import SAMPLE_DOCUMENTS
        schema.documents.insert(SAMPLE_DOCUMENTS)

    export_results()

    count = len(documents) if documents else "sample"
    return _make_response(200, {
        "message": f"Processed {count} records",
        "pixeltable_home": os.environ.get("PIXELTABLE_HOME"),
    })
