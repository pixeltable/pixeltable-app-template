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
# 1. Scaffold
pixeltable init multimodal-rag

# 2. Install
pip install -e ".[openai]"
python -m spacy download en_core_web_sm

# 3. Serve
pixeltable serve
# API available at http://localhost:8000/api
```

Set `OPENAI_API_KEY` for Whisper transcription and chat answers. Without it, document + image + video-frame search still works; audio/video transcription search and `ask_question` are disabled.

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

## Next Steps

- [Computed Columns Tutorial](https://docs.pixeltable.com/tutorials/computed-columns) -- understand how pipelines run automatically
- [Embedding Indexes](https://docs.pixeltable.com/tutorials/similarity-search) -- vector search internals
- [RAG Cookbook](https://docs.pixeltable.com/howto/rag) -- advanced retrieval patterns
- [Deployment Guide](https://docs.pixeltable.com/howto/deployment/overview) -- production infrastructure
