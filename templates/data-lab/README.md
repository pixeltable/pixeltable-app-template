# Data Lab -- ML Dataset Engineering

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
  │     Vision LLM      dedup       control   COCO
  │                                           Label Studio
  ▼
datalab.dataset table
```

## Quickstart

### 1. Install

```bash
uv sync --extra detection --extra export
# Optional: uv sync --extra openai for vision LLM annotations
```

### 2. Initialize & Ingest

```python
import schema  # creates tables, computed columns, and indexes

import pixeltable as pxt
dataset = pxt.get_table('datalab.dataset')

dataset.insert([
    {'image': 'path/to/image1.jpg', 'label': 'cat', 'split': 'train', 'source': 'coco'},
    {'image': 'path/to/image2.jpg', 'label': 'dog', 'split': 'val', 'source': 'coco'},
])
```

### 3. Search & Curate

```python
from schema import search_similar, find_similar_images, dataset_stats

# Find images matching a text description
results = search_similar('a dog running on grass', limit=20)

# Find duplicates / near-duplicates
similar = find_similar_images(image_uuid='...', limit=10)

# Dataset overview
stats = dataset_stats()
```

## Export Formats

```python
from export import export_to_pytorch, export_to_parquet, export_to_coco

# PyTorch DataLoader
train_ds = export_to_pytorch(split='train')
loader = torch.utils.data.DataLoader(train_ds, batch_size=32)

# Parquet (for Spark, DuckDB, pandas)
export_to_parquet('exports/dataset.parquet')

# COCO format (requires DETR detections)
export_to_coco()
```

## API Server

```bash
uv run python schema.py           # initialize tables
uv run pxt serve datalab           # http://localhost:8000/docs
```

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/search` | CLIP similarity search by text |
| POST | `/api/ingest` | Upload + insert an image |
| GET | `/api/annotations` | Retrieve auto-generated annotations |
| GET | `/api/stats` | Label/split distribution |

## Auto-Annotation Pipeline

**Always on (computed columns):**
- **DETR Object Detection** -- `facebook/detr-resnet-50` detects objects and produces bounding boxes, labels, and scores.
- **CLIP Embeddings** -- `openai/clip-vit-base-patch32` enables text-to-image and image-to-image similarity search.

**Optional (requires `OPENAI_API_KEY`):**
- **Vision LLM Classification** -- GPT-4o-mini classifies each image into a single category.

All annotations run automatically on insert -- no manual labeling step.

## Project Structure

```
data-lab/
├── schema.py        # Table definitions, computed columns, query functions
├── export.py        # PyTorch, Parquet, COCO export helpers
├── pyproject.toml   # Dependencies and service routes
└── README.md
```
