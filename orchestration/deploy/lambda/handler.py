"""AWS Lambda handler for the Pixeltable batch pipeline.

Wraps pipeline.py for Lambda execution. Triggered by SQS, S3 events,
EventBridge schedules, or direct invocation.

Environment:
    PIXELTABLE_HOME    Must be /tmp/pixeltable (Lambda's writable directory)
    SERVING_DB_URL     SQLAlchemy connection string for export target
    OPENAI_API_KEY     Optional — enables LLM summary column
"""

import json
import os

os.environ.setdefault("PIXELTABLE_HOME", "/tmp/pixeltable")


def lambda_handler(event, context):
    from pipeline import export_results, verify_search
    import schema

    records = event.get("Records", [])

    if records:
        documents = []
        for record in records:
            if "body" in record:
                body = json.loads(record["body"])
                if isinstance(body, list):
                    documents.extend(body)
                elif isinstance(body, dict):
                    documents.append(body)
        if documents:
            schema.documents.insert(documents)
    else:
        from pipeline import SAMPLE_DOCUMENTS
        schema.documents.insert(SAMPLE_DOCUMENTS)

    export_results()

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"Processed {len(records) or 'sample'} records",
            "pixeltable_home": os.environ.get("PIXELTABLE_HOME"),
        }),
    }
