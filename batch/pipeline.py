"""Batch pipeline: ingest, compute, export.

Usage:
    pxt schema update app.py pipeline      # once, or whenever app.py changes
    python pipeline.py                     # process sample_batch.json
    python pipeline.py --input batch.json  # process a custom JSON file

pipeline.py also applies the models if the catalog is empty, so a job
container can run this file as its only command.

Environment:
    SERVING_DB_URL   SQLAlchemy connection string (default: sqlite:///serving.db)
"""

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path

from app import Documents, Images, Sentences, TableModel
from pixeltable.io.sql import export_sql

SERVING_DB_URL = os.getenv("SERVING_DB_URL", "sqlite:///serving.db")
SAMPLE_BATCH = Path(__file__).parent / "sample_batch.json"


def load_batch(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def export_results() -> None:
    export_sql(
        Documents.select(Documents.source_id, Documents.title, Documents.body, Documents.uuid, Documents.timestamp),
        "processed_documents",
        db_connect_str=SERVING_DB_URL,
        if_exists="replace",
    )
    print(f"  Documents -> {SERVING_DB_URL}:processed_documents")

    export_sql(
        Images.select(Images.source_id, Images.label, Images.width, Images.height, Images.mode),
        "processed_images",
        db_connect_str=SERVING_DB_URL,
        if_exists="replace",
    )
    print(f"  Images    -> {SERVING_DB_URL}:processed_images")


def verify_search() -> None:
    query = "how does Pixeltable handle orchestration?"
    sim = Sentences.text.similarity(string=query)
    results = Sentences.where(sim > 0.3).order_by(sim, asc=False).select(Sentences.text, score=sim).limit(3).collect()
    print(f"\n  Search: '{query}' ({len(results)} hits)")
    for row in results:
        print(f"    [{row['score']:.2f}] {row['text'][:100]}...")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pixeltable batch pipeline")
    parser.add_argument("--input", default=str(SAMPLE_BATCH), help="JSON batch file")
    args = parser.parse_args()

    TableModel.update_all("pipeline")

    t0 = time.time()
    now = datetime.now()

    batch = load_batch(args.input)
    print(f"Loaded {args.input}")

    documents = batch.get("documents", [])
    for row in documents:
        row.setdefault("timestamp", now)
    print(f"Inserting {len(documents)} documents...")
    Documents.insert(documents)

    images = batch.get("images", [])
    if images:
        for row in images:
            row.setdefault("timestamp", now)
        print(f"Inserting {len(images)} images...")
        Images.insert(images)

    print("Exporting...")
    export_results()
    verify_search()

    print(f"\nDone in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
