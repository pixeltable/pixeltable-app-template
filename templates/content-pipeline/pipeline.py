"""Batch processing runner -- alternative to `pxt serve` for offline/scheduled workloads.

Usage:
    python pipeline.py                           # interactive demo with sample data
    python pipeline.py --file urls.json          # ingest from JSON file
    python pipeline.py --urls img.png doc.pdf    # ingest from CLI args
    python pipeline.py --export-parquet out/     # export processed data to Parquet
"""

import argparse
import json
import mimetypes
from datetime import datetime
from pathlib import Path

import schema  # noqa: F401 -- triggers table/view creation on import
from functions import get_processing_status
from schema import (
    audio_files,
    documents,
    images,
    media,
    search_documents,
)

MIME_TO_MODALITY = {
    "image": "image",
    "application": "document",
    "text": "document",
    "audio": "audio",
    "video": "video",
}

EXTENSION_OVERRIDES = {
    ".pdf": "document",
    ".docx": "document",
    ".doc": "document",
    ".pptx": "document",
    ".xlsx": "document",
    ".txt": "document",
    ".html": "document",
    ".htm": "document",
    ".md": "document",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".gif": "image",
    ".webp": "image",
    ".bmp": "image",
    ".tiff": "image",
    ".mp3": "audio",
    ".wav": "audio",
    ".flac": "audio",
    ".m4a": "audio",
    ".ogg": "audio",
    ".aac": "audio",
    ".mp4": "video",
    ".mov": "video",
    ".avi": "video",
    ".mkv": "video",
}


def detect_modality(url: str) -> str:
    ext = Path(url).suffix.lower()
    if ext in EXTENSION_OVERRIDES:
        return EXTENSION_OVERRIDES[ext]
    mime, _ = mimetypes.guess_type(url)
    if mime:
        major = mime.split("/")[0]
        return MIME_TO_MODALITY.get(major, "document")
    return "document"


def ingest_url(url: str, tags: dict | None = None) -> None:
    modality = detect_modality(url)
    now = datetime.now()
    tag_data = tags or {}

    media.insert(
        [
            {
                "url": url,
                "media_type": modality,
                "tags": tag_data,
                "timestamp": now,
            }
        ]
    )

    if modality == "image":
        images.insert([{"image": url, "source_url": url, "timestamp": now}])
    elif modality == "document":
        title = Path(url).stem.replace("_", " ").replace("-", " ")
        documents.insert([{"document": url, "title": title, "timestamp": now}])
    elif modality == "audio":
        title = Path(url).stem.replace("_", " ").replace("-", " ")
        audio_files.insert([{"audio": url, "title": title, "timestamp": now}])
    # video: registered in media table only (no dedicated processing table yet)


def ingest_from_file(json_path: str) -> int:
    """Ingest URLs from a JSON file. Expected format: [{"url": "...", "tags": {...}}, ...]"""
    data = json.loads(Path(json_path).read_text())
    if isinstance(data, list):
        for item in data:
            url = item if isinstance(item, str) else item["url"]
            tags = item.get("tags") if isinstance(item, dict) else None
            ingest_url(url, tags)
        return len(data)
    raise ValueError(f"Expected JSON array, got {type(data).__name__}")


def export_results(parquet_dir: str) -> None:
    from pixeltable.io import export_parquet

    out = Path(parquet_dir)
    out.mkdir(parents=True, exist_ok=True)
    print(f"Exporting to {out}/")

    export_parquet(images.select(images.uuid, images.source_url, images.width, images.height), out / "images")
    print("  images -> done")

    export_parquet(
        schema.doc_chunks.select(schema.doc_chunks.text, schema.doc_chunks.page),
        out / "doc_chunks",
    )
    print("  doc_chunks -> done")


def print_status() -> None:
    status = get_processing_status()
    print("\n--- Processing Status ---")
    for k, v in status.items():
        print(f"  {k}: {v}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Content pipeline batch runner")
    parser.add_argument("--file", help="JSON file with URLs to ingest")
    parser.add_argument("--urls", nargs="+", help="URLs or file paths to ingest")
    parser.add_argument("--search", help="Run a document search query")
    parser.add_argument("--export-parquet", metavar="DIR", help="Export results to Parquet")
    # Export to SQL: use export_sql for Postgres/Snowflake/SQLite
    # from pixeltable.io.sql import export_sql
    # export_sql(images, 'processed_images', db_connect_str='postgresql://user:pass@host/db')
    parser.add_argument("--status", action="store_true", help="Show processing status")
    args = parser.parse_args()

    if args.file:
        count = ingest_from_file(args.file)
        print(f"Ingested {count} items from {args.file}")

    if args.urls:
        for url in args.urls:
            ingest_url(url)
            print(f"Ingested: {url} ({detect_modality(url)})")

    if args.search:
        results = search_documents(args.search, limit=5).collect()
        print(f'\nSearch results for "{args.search}":')
        for row in results:
            print(f"  [{row['score']:.3f}] {row['text'][:120]}")

    if args.export_parquet:
        export_results(args.export_parquet)

    if args.status or not any([args.file, args.urls, args.search, args.export_parquet]):
        print_status()

    if not any([args.file, args.urls, args.search, args.export_parquet, args.status]):
        print("Run with --help for usage, or use `pxt serve pipeline` for the API server.")


if __name__ == "__main__":
    main()
