# Pixeltable Starter Kit

[Pixeltable](https://github.com/pixeltable/pixeltable) is **open-source data infrastructure for AI** — tables, computed columns, and embedding indexes replace the usual patchwork of blob storage, vector DBs, media pipelines, and orchestration glue. This repo shows three ways to build on it, plus seven ready-to-scaffold application templates. Tested against **Pixeltable 0.6.5** (`pixeltable>=0.6.5`).

## Quick start

**Prerequisites:** Python 3.10+, [uv](https://docs.astral.sh/uv/), Node.js 18+ (for UIs).

### Option A — scaffold a full-stack app (recommended)

```bash
uvx pixeltable-new --template full-stack-showcase myapp
cd myapp && cp .env.example .env   # add GEMINI_API_KEY
uv sync && uv run python app.py    # http://localhost:8000

# Frontend (new terminal)
cd frontend && npm install && npm run dev   # http://localhost:5173
```

Run `uvx pixeltable-new --list` for all templates.

### Option B — explore this monorepo

```bash
git clone https://github.com/pixeltable/pixeltable-starter-kit.git
cd pixeltable-starter-kit
cp .env.example .env   # ANTHROPIC_API_KEY, OPENAI_API_KEY

cd backend && uv sync && python main.py   # http://localhost:8000 (schema auto-inits)

# Frontend (new terminal)
cd frontend && npm install && npm run dev   # http://localhost:5173
```

`main.py` imports the schema on startup — no separate init step required. To wipe and recreate: `RESET_SCHEMA=true python setup_pixeltable.py` in `backend/`.

**Production:** `cd frontend && npm run build` then `cd ../backend && python main.py` — serves UI + API on `:8000`.

Open in a [Dev Container](#dev-container) (`.devcontainer/`) for zero local setup.

---

## Choose your path

| I want to… | Start here |
|---|---|
| Build a full-stack AI app fast | [Application templates](#application-templates) via `uvx pixeltable-new --template …` |
| Custom FastAPI API (+ reference React UI in this repo) | [`backend/`](backend/) — headless when scaffolded with `--backend` |
| Batch/cron/queue processing, no HTTP | [`batch/`](batch/) |
| REST API from TOML, zero web code | [`serving/`](serving/) + `pxt serve` |

Pixeltable is a **data engine**, not an HTTP framework. Pick the thinnest wrapper for your workload.

### Project structure

```
backend/          FastAPI API (+ reference React UI via frontend/)
serving/          Declarative API (pxt serve + pyproject.toml routes)
batch/            Batch script (ingest → compute → export_sql → exit)
templates/        Seven scaffoldable apps (fetched by pixeltable-new)
frontend/         React UI for the backend/ pattern
deploy/           Platform deploy configs → see deploy/README.md
```

---

## Patterns

### API Backend — [`backend/`](backend/)

FastAPI + Pixeltable with three demo features: **Data** (upload → auto-processing), **Search** (cross-modal similarity), **Agent** (tool-calling pipeline as 11 computed columns). This monorepo includes a reference [`frontend/`](frontend/); `uvx pixeltable-new --backend` scaffolds the API only.

```bash
cd backend && uv sync && python main.py
```

### Batch Processing — [`batch/`](batch/)

Ingest data, let computed columns process it, export via [`export_sql`](https://docs.pixeltable.com/howto/cookbooks/data/data-export-sql), exit. No HTTP server.

```bash
cd batch && uv sync
PIXELTABLE_HOME=/tmp/pxt uv run python pipeline.py
```

See [`batch/README.md`](batch/) for Cloud Run, K8s Job, ECS, and Lambda configs.

### Declarative Serving — [`serving/`](serving/)

Schema in Python, routes in TOML, API from `pxt serve` — no routers or endpoint handlers.

```bash
cd serving && uv sync
uv run python schema.py && uv run pxt serve pipeline   # http://localhost:8000/docs
```

See [`serving/README.md`](serving/) and [`serving/deploy/pixeltable-cloud/`](serving/deploy/pixeltable-cloud/) for Pixeltable Cloud deployment notes.

---

## Application templates

Scaffold with [`pixeltable-new`](https://github.com/pixeltable/pixeltable-new):

```bash
uvx pixeltable-new --template <name> my-app
cd my-app && uv sync
```

**app.py templates** — run `python app.py` (schema init is automatic). **pxt-serve templates** — run `python schema.py` then `pxt serve <name>`.

| Template | Entry point | What you get |
|----------|------------|--------------|
| [`knowledge-base`](templates/knowledge-base/) | `python app.py` | Multimodal upload, search, RAG Q&A. Web UI |
| [`chat-agent`](templates/chat-agent/) | `python app.py` | Persistent agent, memory, tools, MCP. Web UI |
| [`audio-transcription`](templates/audio-transcription/) | `python app.py` | Transcription, summarization, search. Web UI |
| [`full-stack-showcase`](templates/full-stack-showcase/) | `python app.py` | Gemini + DETR + Whisper, React UI, dashboard |
| [`video-search`](templates/video-search/) | `pxt serve videointel` | Frames, transcription, detection, search. API only |
| [`media-indexing`](templates/media-indexing/) | `pxt serve pipeline` | S3 ingest, multi-modal processing, DB export |
| [`image-dataset`](templates/image-dataset/) | `pxt serve datalab` | Auto-annotate, curate, version, export |

---

## Deploy

| Target | Guide |
|--------|-------|
| Docker Compose, Fly, Render, Railway, Helm, Terraform, CDK, Vercel | [`deploy/README.md`](deploy/README.md) |
| Batch jobs (Cloud Run, K8s, ECS, Lambda) | [`batch/deploy/`](batch/deploy/) |

All production deploys need persistent storage for `PIXELTABLE_HOME`.

---

## Resources

### Swapping AI providers

Default models use **Anthropic** (agent) and **OpenAI** (transcription); embeddings run locally via HuggingFace. Pixeltable supports [20+ providers](https://docs.pixeltable.com/integrations/frameworks). To swap, update computed columns in `backend/setup_pixeltable.py` or your template's `schema.py`. See [LLM tool calling](https://docs.pixeltable.com/howto/cookbooks/agents/llm-tool-calling).

### AI-assisted development

- [Building with LLMs](https://docs.pixeltable.com/overview/building-pixeltable-with-llms) · [llms.txt](https://docs.pixeltable.com/llms.txt)
- [MCP Server](https://github.com/pixeltable/mcp-server-pixeltable-developer) · [Claude Code Skill](https://github.com/pixeltable/pixeltable-skill)
- [AGENTS.md](AGENTS.md) — architecture guide for this repo

### Dev Container

Open in [VS Code Dev Containers](https://containers.dev/) or [GitHub Codespaces](https://github.com/features/codespaces). Auto-installs Python 3.12, Node 20, uv, and dependencies. VS Code: **Dev Containers: Reopen in Container**.

### Learn more

[Pixeltable Docs](https://docs.pixeltable.com/) · [10-Minute Tour](https://docs.pixeltable.com/overview/ten-minute-tour) · [Cookbooks](https://docs.pixeltable.com/howto/cookbooks)

**Use cases:** [ML Data Wrangling](https://docs.pixeltable.com/use-cases/ml-data-wrangling) · [Backend for AI Apps](https://docs.pixeltable.com/use-cases/ai-applications) · [Agents & MCP](https://docs.pixeltable.com/use-cases/agents-mcp)

**Migrating from:** [DIY Pipelines](https://docs.pixeltable.com/migrate/from-diy-data-pipeline) · [RDBMS & Vector DBs](https://docs.pixeltable.com/migrate/from-rdbms-vectordbs) · [Agent Frameworks](https://docs.pixeltable.com/migrate/from-agent-frameworks)

## License

Apache 2.0
