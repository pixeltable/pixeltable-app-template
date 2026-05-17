# Multimodal RAG -- Unified Knowledge Base

Upload docs, images, video, and audio. Search across all media types with one query. Your own Vectara, self-hosted.

## What This Replaces

| Incumbent | Typical Cost | What You Needed |
|-----------|-------------|-----------------|
| Vectara | $2K--50K/yr | Managed RAG API, per-query pricing |
| Cohere RAG | Usage-based | Embedding + reranking API calls |
| LangChain + Pinecone/Weaviate | $1K--20K/yr | Orchestrator + vector DB + glue code |

This template gives you the same multimodal retrieval pipeline in **one Python file**, running on your own infrastructure.

## Quickstart

```bash
# 1. Install
pip install -e ".[openai]"
python -m spacy download en_core_web_sm

# 2. Launch (UI + API)
python app.py
# Open http://localhost:8000
```

Set `OPENAI_API_KEY` for Whisper transcription and chat answers. Without it, document + image + video-frame search still works; audio/video transcription search and the Ask AI tab are disabled.

For API-only mode (no UI): `pxt serve`

## What Pixeltable Handles Automatically

When you insert media into any table, Pixeltable runs the full pipeline with zero application code:

- **Documents** -- sentence/token chunking via `document_splitter`, text embedding with MiniLM, cosine similarity index
- **Images** -- CLIP embedding for visual search, auto-generated 320x320 thumbnails
- **Video** -- frame extraction at 1 fps with CLIP embedding, audio track extraction, 30s segment splitting, Whisper transcription, sentence chunking with text embedding
- **Audio** -- 30s segment splitting, Whisper transcription, sentence chunking with text embedding

All indexes stay current as new data arrives. No cron jobs, no reindex scripts, no sync logic.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/search` | Cross-modal search across all media |
| POST | `/api/ask` | RAG question-answering with LLM |
| POST | `/api/ingest/document` | Upload a document (PDF, HTML, MD) |
| POST | `/api/ingest/image` | Upload an image |
| POST | `/api/ingest/video` | Upload a video |
| POST | `/api/ingest/audio` | Upload an audio file |

## Files

```
multimodal-rag/
├── schema.py         Tables, views, indexes, computed columns, query functions
├── functions.py      UDFs (merge_results)
├── app.py            FastAPI server — API + web UI
├── static/
│   └── index.html    Frontend (Tailwind CSS, vanilla JS)
├── pyproject.toml    Dependencies + pxt serve routes
└── README.md
```

## Next Steps

- [Computed Columns Tutorial](https://docs.pixeltable.com/tutorials/computed-columns) -- understand how pipelines run automatically
- [Embedding Indexes](https://docs.pixeltable.com/tutorials/similarity-search) -- vector search internals
- [RAG Cookbook](https://docs.pixeltable.com/howto/rag) -- advanced retrieval patterns
- [Deployment Guide](https://docs.pixeltable.com/howto/deployment/overview) -- production infrastructure
