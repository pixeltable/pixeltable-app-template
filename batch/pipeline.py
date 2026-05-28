"""Batch pipeline: ingest, compute, export.

Usage:
    python pipeline.py                     # process sample_batch.json
    python pipeline.py --input batch.json  # process a custom JSON file

Environment:
    SERVING_DB_URL   SQLAlchemy connection string (default: sqlite:///serving.db)
    OPENAI_API_KEY   Enables LLM summary column in schema.py
"""

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path

import schema
from pixeltable.io.sql import export_sql

SERVING_DB_URL = os.getenv("SERVING_DB_URL", "sqlite:///serving.db")
SAMPLE_BATCH = Path(__file__).parent / "sample_batch.json"


def load_batch(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def export_results():
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


def verify_search():
    query = "how does Pixeltable handle orchestration?"
    sim = schema.sentences.text.similarity(string=query)
    results = (
        schema.sentences.where(sim > 0.3)
        .order_by(sim, asc=False)
        .select(schema.sentences.text, sim=sim)
        .limit(3)
        .collect()
    )
    print(f"\n  Search: '{query}' ({len(results)} hits)")
    for row in results:
        print(f"    [{row['sim']:.2f}] {row['text'][:100]}...")


def main():
    parser = argparse.ArgumentParser(description="Pixeltable batch pipeline")
    parser.add_argument("--input", default=str(SAMPLE_BATCH), help="JSON batch file")
    args = parser.parse_args()

    t0 = time.time()
    now = datetime.now()

    batch = load_batch(args.input)
    print(f"Loaded {args.input}")

    # 1. Insert documents (computed columns fire: chunking, embeddings, optional LLM summary)
    documents = batch.get("documents", [])
    for row in documents:
        row.setdefault("timestamp", now)
    print(f"Inserting {len(documents)} documents...")
    schema.documents.insert(documents)

    # 2. Insert images (thumbnails + metadata computed automatically)
    images = batch.get("images", [])
    if images:
        for row in images:
            row.setdefault("timestamp", now)
        print(f"Inserting {len(images)} images...")
        schema.images.insert(images)

    # 3. Export to serving DB
    print("Exporting...")
    export_results()

    # 4. Verify semantic search works
    verify_search()

    print(f"\nDone in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
