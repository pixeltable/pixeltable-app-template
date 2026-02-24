# Pixeltable App Template

A full-stack starter repo showing how to build AI applications with [Pixeltable](https://github.com/pixeltable/pixeltable) as the backend. Upload documents, images, and videos — Pixeltable automatically chunks, embeds, transcribes, and indexes everything. Then search across all modalities or chat with a tool-calling agent that queries your data.

## What This Demonstrates

| Pixeltable Feature | Where |
|---|---|
| Tables + multimodal types (`Document`, `Image`, `Video`) | `setup_pixeltable.py` |
| Views + Iterators (`DocumentSplitter`, `FrameIterator`, `AudioSplitter`, `StringSplitter`) | `setup_pixeltable.py` |
| Computed columns (thumbnails, audio extraction, Whisper transcription) | `setup_pixeltable.py` |
| Embedding indexes (`sentence_transformer`, `clip`) + `.similarity()` | Search tab |
| `@pxt.udf` (custom Python functions) | `functions.py` |
| `@pxt.query` (reusable parameterized queries) | `setup_pixeltable.py` |
| `pxt.tools()` + `invoke_tools()` (LLM tool calling) | Agent tab |
| Pydantic row models (validated inserts) | `models.py` |
| On-demand ML inference (DETR object detection) | Data tab |

## Getting Started

**Prerequisites:** Python 3.10+, Node.js 18+

**Required API keys:** `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`

```bash
# 1. Clone
git clone https://github.com/pixeltable/pixeltable-app-template.git
cd pixeltable-app-template

# 2. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Configure
cp ../.env.example .env
# Edit .env with your API keys

# 4. Initialize Pixeltable schema
python setup_pixeltable.py

# 5. Start backend
python main.py  # http://localhost:8000

# 6. Frontend (new terminal)
cd frontend
npm install
npm run dev     # http://localhost:5173 -> proxies /api to :8000
```

**Production build:**

```bash
cd frontend && npm run build   # -> backend/static/
cd ../backend && python main.py  # serves both at :8000
```

## Project Structure

```
backend/
├── main.py                 FastAPI app, CORS, static serving
├── config.py               Model IDs, system prompts, parameters
├── models.py               Pydantic row models for Pixeltable inserts
├── functions.py            @pxt.udf definitions (web search, context assembly)
├── setup_pixeltable.py     Full multimodal schema (tables, views, indexes, agent)
├── requirements.txt
└── routers/
    ├── data.py             Upload, list, detail, frames, transcription, detection
    ├── search.py           Cross-modal similarity search
    └── agent.py            Tool-calling agent + conversations

frontend/src/
├── App.tsx                 Tab navigation (Data / Search / Agent)
├── components/
│   ├── data/               Upload, browse, inspect computed outputs
│   ├── search/             Cross-modal similarity search
│   ├── agent/              Chat with tool-calling agent
│   └── ui/                 Shared UI components
├── lib/api.ts              Typed fetch wrapper
└── types/index.ts          Shared interfaces
```

## The App

Three tabs, each showcasing different Pixeltable capabilities:

**Data** — Upload documents, images, and videos. Browse Pixeltable's computed outputs: document chunks, image thumbnails, video keyframes, transcriptions. Run on-demand object detection.

**Search** — Cross-modal similarity search across all uploaded data. One query searches documents, images, video frames, and transcripts simultaneously via Pixeltable embedding indexes.

**Agent** — Chat with a tool-calling agent (Anthropic Claude) that can search your documents, images, and videos using `pxt.tools()` and `invoke_tools()`.

## Related

- [Pixeltable](https://github.com/pixeltable/pixeltable) — The core library
- [Pixelbot](https://github.com/pixeltable/pixelbot) — Full-featured app this template is distilled from
- [Documentation](https://docs.pixeltable.com/)
- [Cookbooks](https://docs.pixeltable.com/howto/cookbooks)

## License

Apache 2.0
