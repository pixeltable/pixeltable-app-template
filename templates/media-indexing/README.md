# Content Pipeline: Enterprise Media Processing

Ingest media from S3/URLs, auto-process across modalities, export structured results to your database. Your own Cloudinary AI processing layer, self-hosted.

**What it replaces:** Cloudinary AI Transform ($5K-50K/yr), Azure Content Understanding pipelines, custom media processing microservices.

## What You Get

| Modality | Processing | Search |
|----------|-----------|--------|
| Images | Thumbnails, dimensions, mode | Visual metadata listing |
| Documents | Sentence + token chunking, page metadata, embedding index | Semantic search over chunks |
| Audio | 30s segment splitting | Registry + listing |

## Quickstart

Python 3.11+. `pixeltable.toml` is the project root. `pipeline` is a catalog directory, not a folder on disk.

```bash
uv sync
uv run pxt schema update app.py pipeline
uv run pxt service update app.py pipeline
uv run pxt service list
```

Foreground:

```bash
uv run pxt schema update app.py pipeline
uv run pxt service run app.py pipeline --port 8000
```

Or run batch processing instead (applies the models if needed):

```bash
uv run python pipeline.py --urls path/to/image.png path/to/report.pdf path/to/audio.mp3
uv run python pipeline.py --status
```

## Two Modes

### HTTP API (`pxt service`)

Routes are declared on a `FastAPIRouter` in `app.py`:

```
POST /api/search          semantic search over document chunks
POST /api/ingest/image    upload + process an image
POST /api/ingest/document upload + process a document
POST /api/ingest/audio    upload + process audio
```

### Batch Processing (`python pipeline.py`)

```bash
python pipeline.py --file urls.json            # ingest from JSON
python pipeline.py --urls s3://bucket/img.png  # ingest from CLI
python pipeline.py --search "quarterly revenue" # search documents
python pipeline.py --export-parquet output/    # export to Parquet
python pipeline.py --status                    # show counts
```

## Cloud I/O Patterns

### Importing from S3

Pixeltable resolves S3 URLs natively. Pass them as source URLs:

```python
from app import Documents, Images, TableModel

TableModel.update_all('pipeline')
Images.insert([{'image': 's3://my-bucket/photos/hero.jpg', 'source_url': 's3://my-bucket/photos/hero.jpg'}])
Documents.insert([{'document': 's3://my-bucket/docs/report.pdf', 'title': 'Q4 Report'}])
```

Set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in your environment (or use IAM roles).

### Exporting to Postgres / Snowflake

```python
from pixeltable.io.sql import export_sql
from app import DocChunks, Images, TableModel

TableModel.update_all('pipeline')
export_sql(
    Images.select(Images.uuid, Images.source_url, Images.width, Images.height),
    'processed_images',
    db_connect_str='postgresql://user:pass@host:5432/mydb',
    if_exists='replace',
)
export_sql(
    DocChunks.select(DocChunks.text, DocChunks.page),
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
├── app.py           TableModel classes, indexes, queries, FastAPIRouter
├── pipeline.py      Batch runner
├── pixeltable.toml  Project root
├── pyproject.toml   Dependencies
└── README.md
```

## Optional Features

Add columns in `app.py` to enable:

- Vision captions (GPT-4o-mini, requires `OPENAI_API_KEY`)
- CLIP visual search on `Images`
- Audio transcription on `AudioChunks`
- Document summaries
- Cloud storage via `pxt.Column(..., destination='s3://...')`

## Version Control

```python
import pixeltable as pxt
from app import Media, TableModel

TableModel.update_all('pipeline')
pxt.create_snapshot('pipeline.snapshot_v1', Media.table, if_exists='ignore')
```
