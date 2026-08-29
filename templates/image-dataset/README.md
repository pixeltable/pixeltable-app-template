# Data Lab: ML Dataset Engineering

Import, auto-annotate, curate with embedding search, version, and export to PyTorch/Parquet. Your own Roboflow, self-hosted.

## What It Replaces

| SaaS | Typical Cost | What Data Lab Covers |
|------|-------------|---------------------|
| Labelbox | $10K+/yr | Auto-annotation, label management, versioning |
| Scale AI | $25K+/yr | Object detection annotation, structured labeling |
| Roboflow | $5K-50K/yr | Dataset curation, embedding search, export |

## Workflow

```
Import → Auto-Annotate → Curate → Version → Export
  │          │              │         │         │
  │     DETR object     CLIP sim    Built-in  PyTorch
  │     detection +     search +    version   Parquet
  │     labels          dedup       control   COCO
  ▼
datalab.dataset table
```

## Quickstart

Python 3.11+. `pixeltable.toml` is the project root. `datalab` is a catalog directory, not a folder on disk.

### 1. Install

```bash
uv sync --extra export
```

### 2. Apply schema

```bash
uv run pxt schema update app.py datalab
```

### 3. Ingest (SDK)

```python
from app import Dataset, TableModel

TableModel.update_all('datalab')
Dataset.insert([
    {'image': 'path/to/image1.jpg', 'label': 'cat', 'split': 'train', 'source': 'coco'},
    {'image': 'path/to/image2.jpg', 'label': 'dog', 'split': 'val', 'source': 'coco'},
])
```

### 4. Search and curate

```python
from app import dataset_stats, find_similar_images, search_similar

results = search_similar('a dog running on grass', limit=20).collect()
similar = find_similar_images(image_uuid='...', limit=10)
stats = dataset_stats().collect()
```

## Export Formats

```python
from export import export_to_coco, export_to_parquet, export_to_pytorch

train_ds = export_to_pytorch(split='train')
export_to_parquet('exports/dataset.parquet')
export_to_coco()
```

## API Server

```bash
uv run pxt schema update app.py datalab
uv run pxt service update app.py datalab
uv run pxt service list
```

Foreground on port 8000:

```bash
uv run pxt service run app.py datalab --port 8000
```

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/search` | CLIP similarity search by text |
| POST | `/api/ingest` | Upload + insert an image |
| GET | `/api/annotations` | Retrieve auto-generated annotations |
| GET | `/api/stats` | Label/split distribution |

## Auto-Annotation Pipeline

Always on (computed columns in `app.py`):

- **DETR object detection:** `facebook/detr-resnet-50` detects objects and produces bounding boxes, labels, and scores.
- **CLIP embeddings:** `openai/clip-vit-base-patch32` enables text-to-image and image-to-image similarity search.

All annotations run automatically on insert.

## Project Structure

```
image-dataset/
├── app.py           TableModel, indexes, queries, FastAPIRouter
├── export.py        PyTorch, Parquet, COCO export helpers
├── pixeltable.toml  Project root
├── pyproject.toml   Dependencies
└── README.md
```
