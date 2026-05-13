"""Batch pipeline: ingest → compute → export.

Ingests data from a source (JSON file, RDBMS, or sample data), processes it
through Pixeltable computed columns (chunking, embeddings, thumbnails), and
exports structured results to a serving database via export_sql.

Usage:
    python pipeline.py                              # process sample data
    python pipeline.py --input batch.json           # process a JSON batch
    python pipeline.py --input-db 'postgresql://…'  # pull from source DB

Environment:
    SERVING_DB_URL   SQLAlchemy connection string (default: sqlite:///serving.db)
    OPENAI_API_KEY   Enables LLM summary column
    MEDIA_DEST       Cloud URI for generated media (e.g. s3://bucket/out)
"""

import argparse
import json
import os
import time
from datetime import datetime

from pixeltable.io.sql import export_sql

import schema

SERVING_DB_URL = os.getenv("SERVING_DB_URL", "sqlite:///serving.db")

# ── Sample data ──────────────────────────────────────────────────────────────

SAMPLE_DOCUMENTS = [
    {
        "title": "Introduction to Pixeltable",
        "body": (
            "Pixeltable is data infrastructure for AI that replaces the "
            "patchwork of storage, ETL, vector databases, feature stores, "
            "and orchestration frameworks with a single declarative system. "
            "Tables, computed columns, and embedding indexes handle what "
            "typically requires stitching together S3, Postgres, Pinecone, "
            "Airflow, and LangChain."
        ),
        "source_id": "doc-001",
    },
    {
        "title": "Computed Columns",
        "body": (
            "Computed columns in Pixeltable are declarative transformations "
            "that update incrementally. When you insert new rows, only the "
            "new data flows through the computation graph. This eliminates "
            "the need for manual orchestration, retry logic, and dependency "
            "tracking that plague traditional ML pipelines."
        ),
        "source_id": "doc-002",
    },
    {
        "title": "Export to SQL",
        "body": (
            "Pixeltable's export_sql function sends processed data to any "
            "SQL database — PostgreSQL, MySQL, SQLite, Snowflake, or "
            "TigerData. Type mapping is automatic. This lets you use "
            "Pixeltable as a processing engine while keeping your existing "
            "serving infrastructure."
        ),
        "source_id": "doc-003",
    },
    {
        "title": "Media Processing",
        "body": (
            "Pixeltable handles video, audio, images, and documents "
            "natively. Iterators extract frames, split audio, and chunk "
            "documents. Computed columns can run transcription, OCR, object "
            "detection, or any custom UDF. The destination parameter on "
            "add_computed_column routes generated media directly to cloud "
            "storage buckets."
        ),
        "source_id": "doc-004",
    },
    {
        "title": "Ephemeral Deployment",
        "body": (
            "For batch workloads, Pixeltable can run in an ephemeral "
            "container. Schema setup is idempotent and takes seconds. "
            "Data is ingested, processed through computed columns, and "
            "exported to a serving database. The container then exits. "
            "This pattern works with ECS Fargate Spot, Kubernetes Jobs, "
            "or AWS Batch for cost-efficient processing."
        ),
        "source_id": "doc-005",
    },
]

SAMPLE_IMAGES = [
    {
        "image": "https://raw.githubusercontent.com/pixeltable/pixeltable/main/docs/resources/images/000000000036.jpg",
        "label": "cat",
        "source_id": "img-001",
    },
    {
        "image": "https://raw.githubusercontent.com/pixeltable/pixeltable/main/docs/resources/images/000000000090.jpg",
        "label": "scene",
        "source_id": "img-002",
    },
]

# ── Data loading ─────────────────────────────────────────────────────────────


def load_from_json(path: str) -> list[dict]:
    with open(path) as f:
        return json.load(f)


def load_from_db(db_url: str) -> list[dict]:
    import sqlalchemy as sa

    engine = sa.create_engine(db_url)
    with engine.connect() as conn:
        rows = conn.execute(sa.text("SELECT title, body, source_id FROM documents"))
        return [dict(r._mapping) for r in rows]


# ── Export ───────────────────────────────────────────────────────────────────


def export_results() -> None:
    """Export processed data to the serving database."""
    docs = schema.documents
    imgs = schema.images

    export_sql(
        docs.select(docs.source_id, docs.title, docs.body, docs.uuid, docs.timestamp),
        "processed_documents",
        db_connect_str=SERVING_DB_URL,
        if_exists="replace",
    )
    print(f"  Documents -> {SERVING_DB_URL}:processed_documents")

    export_sql(
        imgs.select(imgs.source_id, imgs.label, imgs.width, imgs.height, imgs.mode),
        "processed_images",
        db_connect_str=SERVING_DB_URL,
        if_exists="replace",
    )
    print(f"  Images    -> {SERVING_DB_URL}:processed_images")


def verify_export() -> None:
    """Quick sanity check: read back from the serving DB."""
    import sqlalchemy as sa

    engine = sa.create_engine(SERVING_DB_URL)
    with engine.connect() as conn:
        doc_rows = conn.execute(
            sa.text("SELECT source_id, title FROM processed_documents")
        ).fetchall()
        img_rows = conn.execute(
            sa.text("SELECT source_id, label, width, height FROM processed_images")
        ).fetchall()

    print(f"\n  Serving DB — processed_documents ({len(doc_rows)} rows):")
    for r in doc_rows:
        print(f"    {r[0]}  {r[1]}")

    print(f"\n  Serving DB — processed_images ({len(img_rows)} rows):")
    for r in img_rows:
        print(f"    {r[0]}  {r[1]:<15s}  {r[2]}x{r[3]}")


def verify_search() -> None:
    """Test semantic search on the ingested documents."""
    query = "how does Pixeltable handle orchestration?"
    sim = schema.sentences.text.similarity(string=query)
    results = (
        schema.sentences.where(sim > 0.3)
        .order_by(sim, asc=False)
        .select(schema.sentences.text, sim=sim)
        .limit(3)
        .collect()
    )
    print(f"\n  Search test — '{query}' ({len(results)} hits):")
    for row in results:
        print(f"    [{row['sim']:.2f}] {row['text'][:100]}...")


# ── Main ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Pixeltable batch pipeline")
    parser.add_argument("--input", help="JSON file with documents to process")
    parser.add_argument("--input-db", help="SQLAlchemy URL to pull documents from")
    parser.add_argument(
        "--skip-images", action="store_true", help="Skip image processing"
    )
    args = parser.parse_args()

    t0 = time.time()
    now = datetime.now()

    # 1. Load data
    if args.input:
        data = load_from_json(args.input)
        print(f"Loaded {len(data)} documents from {args.input}")
    elif args.input_db:
        data = load_from_db(args.input_db)
        print(f"Loaded {len(data)} documents from source DB")
    else:
        data = SAMPLE_DOCUMENTS
        print(f"Using {len(data)} sample documents")

    for row in data:
        row.setdefault("timestamp", now)

    # 2. Insert documents (computed columns fire automatically:
    #    sentence chunking, embeddings, optional LLM summary)
    print("Inserting documents...")
    schema.documents.insert(data)

    # 3. Insert images (thumbnails + metadata generated automatically)
    if not args.skip_images:
        print("Inserting images...")
        img_data = SAMPLE_IMAGES.copy()
        for row in img_data:
            row.setdefault("timestamp", now)
        schema.images.insert(img_data)

    # 4. Export to serving DB
    print("Exporting results...")
    export_results()
    verify_export()

    # 5. Verify search works
    verify_search()

    elapsed = time.time() - t0
    print(f"\nPipeline completed in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
