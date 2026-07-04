# Audio & Podcast Intelligence

Ingest audio files, automatically transcribe, chunk, summarize, and search across recordings. Your own Otter.ai, self-hosted.

## What it replaces

| Service | Cost |
|---------|------|
| Otter.ai | $20/mo per user |
| Descript | $24/mo per user |
| AssemblyAI | $0.37/min |
| **audio-transcription** | **Free + your compute** |

## Use cases

- **Meeting intelligence** -- transcribe and search across every meeting recording
- **Podcast analytics** -- find every mention of a topic across hundreds of episodes
- **Call center QA** -- search agent calls for compliance keywords in seconds
- **Compliance search** -- full-text + semantic search over recorded conversations

## Quickstart

```bash
uv sync                           # install deps
OPENAI_API_KEY=sk-... uv run python app.py
# Open http://localhost:8000
```

That's it. `app.py` initializes the schema and starts the server with the web UI.

To use local Whisper instead of the OpenAI API, install with `uv sync --extra local` and uncomment the local whisper block in `schema.py`.

### API-only mode (no UI)

```bash
OPENAI_API_KEY=sk-... uv run python schema.py
OPENAI_API_KEY=sk-... uv run pxt serve audiointel
```

Do **not** run both `pxt serve` and `app.py` at the same time -- they bind to the same port.

## What Pixeltable handles

All of the following run **automatically** when you insert a row -- zero glue code:

1. **Audio splitting** -- 30-second segments with 5s overlap via `audio_splitter`
2. **Transcription** -- OpenAI Whisper API (or local `whisper.transcribe`)
3. **Sentence chunking** -- spaCy sentence segmentation via `string_splitter`
4. **Embedding** -- `all-MiniLM-L6-v2` sentence embeddings, computed on insert
5. **Indexing** -- HNSW vector index for sub-second semantic search
6. **Summarization** -- per-chunk LLM summaries via `chat_completions`

## API routes

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/upload` | Upload and ingest an audio file (background job) |
| `GET` | `/api/recordings` | List all recordings |
| `POST` | `/api/search` | Semantic search across all transcripts (needs `OPENAI_API_KEY`) |
| `POST` | `/api/search-in` | Search within one recording (needs `OPENAI_API_KEY`) |
| `GET` | `/api/transcript` | Full transcript for a recording (needs `OPENAI_API_KEY`) |
| `GET` | `/api/summary` | Per-chunk summaries for a recording (needs `OPENAI_API_KEY`) |

## Architecture

```
audio file
  └─ audio_files table (audio, title, source, uuid, timestamp)
       └─ chunks view (30s segments via audio_splitter)
            ├─ transcription (openai.transcriptions)
            ├─ summary (chat_completions)
            └─ sentences view (string_splitter)
                 └─ embedding index (all-MiniLM-L6-v2)
```

## Files

```
audio-transcription/
├── schema.py         Tables, views, indexes, computed columns, query functions
├── functions.py      UDFs (generate_full_summary)
├── app.py            FastAPI server — API + web UI
├── static/
│   └── index.html    Frontend (Tailwind CSS, vanilla JS)
├── pyproject.toml    Dependencies + pxt serve routes (API-only alternative)
└── README.md
```
