# Pixeltable App Template

A skeleton app showing how [Pixeltable](https://github.com/pixeltable/pixeltable) unifies **storage, orchestration, and retrieval** for multimodal workloads. Pixeltable is data infrastructure — you can build whatever you want on top of it. This template just demonstrates the core pattern with a simple three-tab UI:

- **Data** — Upload documents, images, and videos. Pixeltable automatically chunks, extracts keyframes, transcribes audio, and generates thumbnails via computed columns and iterators.
- **Search** — Cross-modal similarity search across all media types using embedding indexes.
- **Agent** — Chat with a tool-calling agent (Claude) wired up entirely as Pixeltable computed columns.

> For a more complete example, see **[Pixelbot](https://github.com/pixeltable/pixelbot)**.

## Quick Start

**Prerequisites:** Python 3.10+, Node.js 18+, [uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/pixeltable/pixeltable-app-template.git
cd pixeltable-app-template
cp .env.example .env   # add your ANTHROPIC_API_KEY and OPENAI_API_KEY

# Backend
cd backend
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
python -m spacy download en_core_web_sm
python setup_pixeltable.py   # initialize schema (one-time)
python main.py               # http://localhost:8000

# Frontend (new terminal)
cd frontend
npm install && npm run dev   # http://localhost:5173
```

**Production:** `cd frontend && npm run build` then `cd ../backend && python main.py` — serves everything at `:8000`.

## Project Structure

```
backend/
├── main.py                 FastAPI app, CORS, static serving
├── config.py               Model IDs, system prompts, env overrides
├── models.py               Pydantic row models (agent + chat tables)
├── functions.py            @pxt.udf definitions (web search, context assembly)
├── setup_pixeltable.py     Full multimodal schema (tables, views, indexes, agent)
├── requirements.txt
└── routers/
    ├── data.py             Upload, list, delete, chunks, frames, transcription
    ├── search.py           Cross-modal similarity search
    └── agent.py            Tool-calling agent + conversations

frontend/src/
├── App.tsx                 Tab navigation (Data / Search / Agent)
├── components/             Page components + shared UI (Button, Badge)
├── lib/api.ts              Typed fetch wrapper
└── types/index.ts          Shared interfaces
```

## Pixeltable Schema

Everything in `setup_pixeltable.py`. Drops and recreates the `app` namespace on every run.

### Tables

| Table | Columns | Notes |
|---|---|---|
| `app.documents` | `document (Document)`, `uuid (uuid7() PK)`, `timestamp`, `user_id` | Auto-generated UUID primary key |
| `app.images` | `image (Image)`, `uuid (uuid7() PK)`, `timestamp`, `user_id` | + computed `thumbnail` via `b64_encode(thumbnail())` |
| `app.videos` | `video (Video)`, `uuid (uuid7() PK)`, `timestamp`, `user_id` | + computed `audio` extraction |
| `app.chat_history` | `role`, `content`, `conversation_id`, `timestamp`, `user_id` | Embedding index on `content` |
| `app.agent` | `prompt`, `timestamp`, `user_id`, system prompts, LLM params | 8 computed columns (the pipeline) |

### Views (Iterators)

| View | Source | Iterator |
|---|---|---|
| `app.chunks` | `documents` | `DocumentSplitter` (page + sentence) |
| `app.video_frames` | `videos` | `FrameIterator` (keyframes only) |
| `app.video_audio_chunks` | `videos` | `AudioSplitter` (30s chunks) |
| `app.video_sentences` | `video_audio_chunks` | `StringSplitter` on Whisper transcription |

### Embedding Indexes

| Target | Embed Function |
|---|---|
| `chunks.text` | `sentence_transformer` (multilingual-e5) |
| `images.image` | `clip` (CLIP ViT-B/32) |
| `video_frames.frame` | `clip` (CLIP ViT-B/32) |
| `video_sentences.text` | `sentence_transformer` (multilingual-e5) |
| `chat_history.content` | `sentence_transformer` (multilingual-e5) |

### Agent Pipeline (8 computed columns on `app.agent`)

1. **`initial_response`** — Claude call with tools (`web_search`, `search_video_transcripts`)
2. **`tool_output`** — `invoke_tools()` executes the chosen tool
3. **`doc_context` / `image_context` / `video_frame_context` / `chat_memory_context`** — RAG retrieval via `@pxt.query`
4. **`history_context`** — Recent chat history
5. **`multimodal_context`** — `assemble_context()` merges everything into text
6. **`final_messages`** — `assemble_final_messages()` builds message list with base64 images
7. **`final_response`** — Claude call with assembled messages
8. **`answer`** — Extracts `final_response.content[0].text`

## API Endpoints

### Data (`/api/data`)

| Method | Path | Description |
|---|---|---|
| `POST` | `/upload` | Upload a file (auto-classifies as document/image/video) |
| `GET` | `/files` | List all files grouped by type |
| `DELETE` | `/files/{uuid}/{type}` | Delete a file |
| `GET` | `/chunks/{uuid}` | Document chunks |
| `GET` | `/frames/{uuid}` | Video keyframe thumbnails |
| `GET` | `/transcription/{uuid}` | Video transcription sentences |

### Search (`/api/search`)

`POST /search` — Body: `{ query, types?, limit?, threshold? }`. Types: `document`, `image`, `video_frame`, `transcript`.

### Agent (`/api/agent`)

| Method | Path | Description |
|---|---|---|
| `POST` | `/query` | Send query → returns `{ answer, metadata }` |
| `GET` | `/conversations` | List conversations |
| `GET` | `/conversations/{id}` | Get conversation messages |
| `DELETE` | `/conversations/{id}` | Delete conversation |

## Configuration

All in `config.py`. Override via environment variables:

| Constant | Default | Env Var |
|---|---|---|
| `CLAUDE_MODEL_ID` | `claude-sonnet-4-20250514` | `CLAUDE_MODEL` |
| `EMBEDDING_MODEL_ID` | `intfloat/multilingual-e5-large-instruct` | `EMBEDDING_MODEL` |
| `CLIP_MODEL_ID` | `openai/clip-vit-base-patch32` | `CLIP_MODEL` |
| `WHISPER_MODEL_ID` | `whisper-1` | `WHISPER_MODEL` |

`load_dotenv()` runs once in `config.py` — don't add it elsewhere.

## Conventions

- Media tables use plain dicts for inserts — `uuid7()` auto-generates the primary key. Agent/chat tables use Pydantic models from `models.py`.
- Schema changes → edit `setup_pixeltable.py` and re-run.
- Frontend `toDataUrl()` wraps raw base64 from Pixeltable's `b64_encode()` into `data:image/…` URLs.
- Named exports only; no default exports.

## Learn More

[Pixeltable Docs](https://docs.pixeltable.com/) · [GitHub](https://github.com/pixeltable/pixeltable) · [Cookbooks](https://docs.pixeltable.com/howto/cookbooks)

## License

Apache 2.0
