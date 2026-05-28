# Video Intelligence Pipeline

Ingest video, automatically extract frames, transcribe audio, detect objects, and search across everything. Your own Twelve Labs, self-hosted.

**What it replaces:** Twelve Labs, Valossa, Ambient.ai ($10K–100K+/yr)

**What Pixeltable does declaratively:** the pipeline that would normally require stitching together ffmpeg + Whisper + DETR + CLIP + a vector DB + a search API — defined as tables, views, and computed columns.

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
            │  /search         → combined           │
            └──────────────────────────────────────┘
```

## Quickstart

### 1. Install

```bash
uv sync
# For LLM scene descriptions: uv sync --extra openai
```

### 2. Initialize & serve

```bash
uv run python schema.py           # create tables, views, indexes (idempotent)
uv run pxt serve videointel       # http://localhost:8000/docs
```

The server starts at `http://localhost:8000`. Upload a video:

```bash
curl -X POST http://localhost:8000/api/ingest \
  -F "video=@lecture.mp4" \
  -F "title=ML Lecture 1"
```

Search across all modalities:

```bash
# Visual search — "what does X look like?"
curl -X POST http://localhost:8000/api/search/visual \
  -H "Content-Type: application/json" \
  -d '{"query_text": "person writing on whiteboard"}'

# Spoken content search — "what was said about X?"
curl -X POST http://localhost:8000/api/search/spoken \
  -H "Content-Type: application/json" \
  -d '{"query_text": "gradient descent optimization"}'

# Object detection search — "where does X appear?"
curl -X POST http://localhost:8000/api/search/objects \
  -H "Content-Type: application/json" \
  -d '{"label": "person"}'
```

## What happens on insert

When you upload a video, Pixeltable automatically runs the full pipeline:

1. **Frame extraction** — `frame_iterator` extracts frames at 1 FPS
2. **CLIP embeddings** — each frame gets a visual embedding for semantic image search
3. **Thumbnails** — base64-encoded 320x320 thumbnails for API responses
4. **Object detection** — DETR identifies objects in each frame
5. **Audio extraction** — `extract_audio` pulls the audio track
6. **Audio chunking** — `audio_splitter` creates 30-second segments
7. **Transcription** — Whisper transcribes each audio chunk locally
8. **Sentence splitting** — transcripts are split into sentences
9. **Text embeddings** — sentence-transformer embeddings for spoken content search
10. **Scene descriptions** — GPT-4o-mini describes keyframes (optional, needs `OPENAI_API_KEY`)

All of this is defined declaratively in `schema.py`. No orchestration code, no DAG, no glue.

## Configuration

| Environment Variable | Effect |
|---------------------|--------|
| `OPENAI_API_KEY` | Enables LLM scene descriptions on frames |
| `PIXELTABLE_HOME` | Custom data directory (default `~/.pixeltable`) |

## Project Structure

```
video-search/
├── schema.py          Declarative pipeline: tables, views, indexes, queries
├── pyproject.toml     Dependencies + pxt serve route config
└── README.md          This file
```
