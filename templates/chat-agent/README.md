# Persistent Multimodal Agent

A durable agent where conversations, memory, knowledge, and tool traces are all queryable, versioned Pixeltable tables. Your own Mem0, self-hosted.

**What it replaces:** Mem0 ($5K–30K/yr), MemGPT, custom agent platforms with ephemeral memory.

**Key differentiator:** Tables ARE the memory. Every conversation turn, tool invocation, and knowledge chunk is a row — not ephemeral, fully queryable across sessions, with complete lineage and version history. No separate vector DB, no Redis sidecar, no memory service.

## Quick Start

```bash
uv sync                           # install deps
ANTHROPIC_API_KEY=sk-... uv run python app.py
# Open http://localhost:8000
```

That's it. `app.py` initializes the schema and starts the server with the web UI.

### API-only mode (no UI)

```bash
ANTHROPIC_API_KEY=sk-... uv run python schema.py
ANTHROPIC_API_KEY=sk-... uv run pxt serve agent
```

Do **not** run both `pxt serve` and `app.py` at the same time -- they bind to the same port.

### `/ask` endpoint differences

`app.py` and `pxt serve agent` expose different `/ask` contracts:

| Mode | Endpoint | Behavior |
|------|----------|----------|
| `app.py` | `POST /api/ask` | Custom handler calling `schema.ask()`; body: `{"question": "...", "conversation_id": "..."}`; returns `{"answer": "..."}` |
| `pxt serve agent` | `POST /api/ask` | Insert route into `agent.agent`; body includes `prompt`, `conversation_id`, and optional `system_prompt`, `max_tokens`, `temperature`; returns insert row with computed pipeline columns |

Both trigger the same computed-column agent pipeline; choose based on whether you need the simplified app handler or direct table insert semantics.

## Architecture

Insert a prompt → computed columns fire in sequence → answer comes back:

```
INSERT {prompt, conversation_id}
  │
  ├─ memory_context    ← recall_memory(): semantic search over past conversations
  ├─ knowledge_context ← search_knowledge(): RAG over sentence-chunked knowledge base
  │
  ├─ initial_response  ← Anthropic messages() with tools (web_search, search, recall)
  ├─ tool_output       ← invoke_tools() executes whichever tools the LLM chose
  │
  ├─ context           ← assemble_context() merges memory + knowledge + tool results
  ├─ final_response    ← Anthropic messages() with full assembled context
  └─ answer            ← extracted response text
```

Every step is a column. Every column is queryable, versioned, and debuggable.

## Endpoints

| Method | Path | Type | Description |
|--------|------|------|-------------|
| `POST` | `/api/ask` | insert | Ask the agent (triggers full computed column chain) |
| `POST` | `/api/knowledge` | insert | Add a document to the knowledge base |
| `GET` | `/api/knowledge/search` | query | Semantic search over the knowledge base |
| `GET` | `/api/memory/search` | query | Semantic search across all conversations |
| `GET` | `/api/history` | query | Get recent turns from a conversation |

## Tables

| Table | Purpose |
|-------|---------|
| `agent.knowledge` | Knowledge base documents |
| `agent.sentences` | View: sentence-level chunks with embedding index |
| `agent.conversations` | All messages with role, content, conversation_id, user_id |
| `agent.agent` | Agent pipeline: prompt → computed column chain → answer |

## Python SDK

```python
import schema

# Add knowledge
schema.knowledge.insert([{
    'text': 'Pixeltable is declarative data infrastructure for AI.',
    'title': 'About Pixeltable',
    'source': 'docs',
}])

# Ask the agent (inserts into agent table, saves conversation history)
answer = schema.ask('What is Pixeltable?', conversation_id='sess-1')

# Direct query access — @pxt.query functions return a DataFrame; call .collect()
results = schema.search_knowledge('data infrastructure').collect()
memories = schema.recall_memory('deployment options').collect()
history = schema.get_history('sess-1').collect()
```

## Adding Tools

Register any `@pxt.udf` or `@pxt.query` function as a tool the agent can call:

```python
tools = pxt.tools(web_search, search_knowledge, recall_memory, your_custom_tool)
```

Connect to external services via MCP:

```python
mcp_tools = pxt.mcp_udfs('http://localhost:9000/mcp')
tools = pxt.tools(web_search, search_knowledge, *mcp_tools)
```

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Enables the agent pipeline (LLM + tools) |
| `PIXELTABLE_HOME` | No | Persistent storage (default: `~/.pixeltable`) |

## Files

```
chat-agent/
├── schema.py        Tables, views, indexes, computed columns, tools, query functions
├── functions.py     UDFs (web_search, assemble_context)
├── app.py           FastAPI server — API + web UI
├── static/
│   └── index.html   Frontend (Tailwind CSS, vanilla JS)
├── pyproject.toml   Dependencies + pxt serve routes (API-only alternative)
└── README.md
```
