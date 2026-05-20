# Content Pipeline -- Enterprise Media Processing

Ingest media from S3/URLs, auto-process across modalities, export structured results to your database. Your own Cloudinary AI processing layer, self-hosted.

**What it replaces:** Cloudinary AI Transform ($5K--50K/yr), Azure Content Understanding pipelines, custom media processing microservices.

## What You Get

| Modality | Processing | Search |
|----------|-----------|--------|
| Images | Thumbnails, dimensions, mode, optional CLIP embedding + vision caption | Visual similarity (CLIP) |
| Documents | Sentence + token chunking, page metadata, embedding index | Semantic search over chunks |
| Audio | 30s segment splitting, optional Whisper transcription | -- |

## Quickstart

```bash
uv sync                           # install deps
uv run python schema.py           # initialize tables
uv run pxt serve pipeline         # http://localhost:8000/docs
```

Or run batch processing instead:

```bash
uv run python pipeline.py --urls path/to/image.png path/to/report.pdf path/to/audio.mp3
uv run python pipeline.py --status
```

## Two Modes

### Real-time API (`pxt serve`)

Routes are declared in `pyproject.toml` -- zero web code required:

```
POST /api/search          -- semantic search over document chunks
POST /api/ingest/image    -- upload + process an image
POST /api/ingest/document -- upload + process a document
POST /api/ingest/audio    -- upload + process audio
GET  /api/status          -- item counts per modality
```

### Batch Processing (`python pipeline.py`)

```bash
python pipeline.py --file urls.json            # ingest from JSON
python pipeline.py --urls s3://bucket/img.png   # ingest from CLI
python pipeline.py --search "quarterly revenue" # search documents
python pipeline.py --export-parquet output/     # export to Parquet
python pipeline.py --status                     # show counts
```

## Cloud I/O Patterns

### Importing from S3

Pixeltable resolves S3 URLs natively -- just pass them as source URLs:

```python
images.insert([{'image': 's3://my-bucket/photos/hero.jpg', 'source_url': 's3://my-bucket/photos/hero.jpg', 'timestamp': datetime.now()}])
documents.insert([{'document': 's3://my-bucket/docs/report.pdf', 'title': 'Q4 Report', 'timestamp': datetime.now()}])
```

Set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in your environment (or use IAM roles).

### Exporting to Postgres / Snowflake

```python
from pixeltable.io.sql import export_sql

export_sql(
    images.select(images.uuid, images.source_url, images.width, images.height),
    'processed_images',
    db_connect_str='postgresql://user:pass@host:5432/mydb',
    if_exists='replace',
)

export_sql(
    doc_chunks.select(doc_chunks.text, doc_chunks.page),
    'document_chunks',
    db_connect_str='snowflake://user:pass@account/db/schema',
    if_exists='replace',
)
```

### Exporting to Parquet

```bash
python pipeline.py --export-parquet output/
```

## Project Structure

```
media-indexing/
├── schema.py        -- tables, views, computed columns, query functions
├── pipeline.py      -- batch runner (CLI alternative to pxt serve)
├── pyproject.toml   -- dependencies + pxt serve route config
└── README.md
```

## Optional Features

Uncomment sections in `schema.py` to enable:

- **Vision captions** -- GPT-4o-mini image descriptions (requires `OPENAI_API_KEY`)
- **CLIP visual search** -- image similarity search via `openai/clip-vit-base-patch32`
- **Audio transcription** -- Whisper transcription on audio segments (requires `OPENAI_API_KEY`)
- **Document summaries** -- LLM-generated summaries per document
- **Cloud storage** -- persist computed media to S3 via `destination='s3://...'`

## Version Control

Snapshot your pipeline state before destructive changes:

```python
import pixeltable as pxt
pxt.create_snapshot('pipeline.snapshot_v1', media, if_exists='ignore')
```
