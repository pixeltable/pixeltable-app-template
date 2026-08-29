# Video Intelligence Pipeline

Ingest video, automatically extract frames, transcribe audio, detect objects, and search across everything. Your own Twelve Labs, self-hosted.

**What it replaces:** Twelve Labs, Valossa, Ambient.ai ($10K-100K+/yr)

**What Pixeltable does declaratively:** the pipeline that would normally require stitching together ffmpeg + Whisper + DETR + CLIP + a vector DB + a search API, defined as tables, views, and computed columns.

## Architecture

```
                              ┌─────────────────────┐
                              │   Video (ingested)   │
                              └──────────┬──────────┘
                         ┌───────────────┼───────────────┐
                         ▼               ▼               ▼
                ┌────────────────┐ ┌───────────┐ ┌──────────────┐
                │  Frame Extract │ │   Audio   │ │   Metadata   │
                │  (1 FPS view)  │ │ Extract   │ │   (title,    │
                │                │ │           │ │    uuid)     │
                └───┬────┬───┬──┘ └─────┬─────┘ └──────────────┘
                    │    │   │          │
                    ▼    ▼   ▼          ▼
               ┌────┐ ┌────┐ ┌────┐ ┌────────────┐
               │CLIP│ │DETR│ │LLM │ │Audio Split │
               │Emb.│ │Det.│ │Desc│ │ (30s chunks)│
               └──┬─┘ └──┬─┘ └──┬─┘ └─────┬──────┘
                  │       │      │          ▼
                  │       │      │   ┌─────────────┐
                  │       │      │   │   Whisper    │
                  │       │      │   │ Transcribe   │
                  │       │      │   └──────┬──────┘
                  │       │      │          ▼
                  │       │      │   ┌─────────────┐
                  │       │      │   │  Sentence    │
                  │       │      │   │  Splitter    │
                  │       │      │   └──────┬──────┘
                  │       │      │          ▼
                  ▼       ▼      ▼          ▼
            ┌──────────────────────────────────────┐
            │           Search API                 │
            │  /search/visual  → CLIP similarity   │
            │  /search/spoken  → text similarity   │
            │  /search/objects → label filter       │
            │  /search         → visual (default)   │
            └──────────────────────────────────────┘
```

## Quickstart

Python 3.11+. `pixeltable.toml` is the project root.

### 1. Install

```bash
uv sync
# For LLM scene descriptions: add a computed column in app.py and uv sync --extra openai
```

### 2. Apply and serve

```bash
uv run pxt schema update app.py videointel
uv run pxt service update app.py videointel
uv run pxt service list
```

Foreground on port 8000:

```bash
uv run pxt schema update app.py videointel
uv run pxt service run app.py videointel --port 8000
```

`videointel` is a catalog directory, not a folder on disk.

Upload a video (background job: use the `job_url` from the response):

```bash
curl -s -X POST http://localhost:8000/api/ingest \
  -F "video=@lecture.mp4" \
  -F "title=ML Lecture 1"
```

Search responses return a **`score`** field (CLIP similarity), plus **`thumbnail`** (base64).

```bash
# Visual search
curl -X POST http://localhost:8000/api/search/visual \
  -H "Content-Type: application/json" \
  -d '{"query_text": "person writing on whiteboard"}'

# Spoken content search
curl -X POST http://localhost:8000/api/search/spoken \
  -H "Content-Type: application/json" \
  -d '{"query_text": "gradient descent optimization"}'

# Object detection search
curl -X POST http://localhost:8000/api/search/objects \
  -H "Content-Type: application/json" \
  -d '{"label": "person"}'
```

## What happens on insert

When you upload a video, Pixeltable automatically runs the full pipeline:

1. **Frame extraction:** `frame_iterator` extracts frames at 1 FPS
2. **CLIP embeddings:** each frame gets a visual embedding for semantic image search
3. **Thumbnails:** base64-encoded 320x320 thumbnails for API responses
4. **Object detection:** DETR identifies objects in each frame
5. **Audio extraction:** `extract_audio` pulls the audio track
6. **Audio chunking:** `audio_splitter` creates 30-second segments
7. **Transcription:** Whisper transcribes each audio chunk locally
8. **Sentence splitting:** transcripts are split into sentences
9. **Text embeddings:** sentence-transformer embeddings for spoken content search

All of this is declared in `app.py`. Indexes live on `__indexes__`. Routes live on a `FastAPIRouter`.

## Configuration

| Environment Variable | Effect |
|---------------------|--------|
| `PIXELTABLE_HOME` | Custom data directory (default `~/.pixeltable`) |

## Project Structure

```
video-search/
├── app.py             TableModel classes, indexes, queries, FastAPIRouter
├── functions.py       UDF: has_label object-detection filter
├── pixeltable.toml    Project root
├── pyproject.toml     Dependencies
└── README.md          This file
```
