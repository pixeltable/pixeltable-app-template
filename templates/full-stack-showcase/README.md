# Full-Stack Showcase

**The complete Pixeltable reference implementation** — a production-grade video intelligence
platform that exercises every core primitive in one codebase.

| Layer | What it demonstrates |
|---|---|
| **Schema** | Multimodal tables (video, image, audio, text), computed columns (Gemini, DETR, Whisper), views with iterators, multimodal embedding indexes |
| **Backend** | FastAPI routers, thread-safe `pxt.get_table()`, cross-modal search (text→video, image→video, audio→video), alerting, dashboard |
| **Frontend** | React + TypeScript + Tailwind — 5 pages: Operations, Inspections, Browse, Investigate, Alerts |

## Quick Start

```bash
uvx pixeltable-new --template full-stack-showcase myapp
cd myapp && cp .env.example .env   # add your GEMINI_API_KEY
uv sync && uv run python app.py    # http://localhost:8000

# Frontend (new terminal)
cd frontend && npm install && npm run dev   # http://localhost:5173
```

That's it. `app.py` initializes the schema and starts the server.

### API-only mode (no UI)

```bash
uv sync
uv run python schema.py
uv run pxt serve sitewatch         # http://localhost:8000/docs
```

Do **not** run both `pxt serve` and `app.py` at the same time — they bind to the same port.

## AI Stack

| Component | Model | Purpose |
|---|---|---|
| Video Analysis | Gemini 2.5 Flash | Whole-video summary, segment condition/severity/PPE |
| Audio Transcription | Whisper (local) | Speech-to-text on extracted audio chunks |
| Multimodal Embeddings | Gemini Embedding 2 | Text, image, audio, video in one semantic space |
| Object Segmentation | DETR ResNet-50 Panoptic | Per-frame panoptic segmentation + overlay |
| Scene Detection | PySceneDetect | Content-based scene boundaries |

## Project Structure

```
├── schema.py            # Pixeltable schema (tables, views, indexes, computed columns)
├── config.py            # Configuration and Gemini prompts
├── functions.py         # Shared helpers (Gemini response parsing)
├── app.py               # FastAPI application
├── models.py            # Pydantic response models
├── routers/
│   ├── videos.py        # Upload, list, detail, delete, frames, scenes
│   ├── search.py        # Cross-modal search + related events
│   ├── browse.py        # Multi-medium browsing + DETR detections
│   └── dashboard.py     # ROI metrics, alerts, activity feed
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/  # dashboard, videos, browse, search, alerts
│   │   ├── lib/api.ts
│   │   └── types/
│   └── package.json
├── pyproject.toml
└── .env.example
```

## Without GEMINI_API_KEY

The template works without an API key — you still get:
- Video upload and metadata
- Frame extraction with DETR panoptic segmentation
- Audio extraction + Whisper transcription
- Scene detection

Cross-modal search and LLM analysis require `GEMINI_API_KEY`.
