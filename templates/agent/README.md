# Persistent Multimodal Agent

A durable agent where conversations, memory, knowledge, and tool traces are all queryable, versioned Pixeltable tables. Your own Mem0, self-hosted.

**What it replaces:** Mem0 ($5K–30K/yr), MemGPT, custom agent platforms with ephemeral memory.

**Key differentiator:** Tables ARE the memory. Every conversation turn, tool invocation, and knowledge chunk is a row — not ephemeral, fully queryable across sessions, with complete lineage and version history. No separate vector DB, no Redis sidecar, no memory service.

## Quick Start

```bash
# 1. Install
pip install -e ".[anthropic]"
python -m spacy download en_core_web_sm

# 2. Launch (UI + API)
ANTHROPIC_API_KEY=sk-... python app.py
# Open http://localhost:8000
```

For API-only mode (no UI): `ANTHROPIC_API_KEY=sk-... pxt serve`

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
| `POST` | `/api/memory/search` | query | Semantic search across all conversations |
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

# Direct query access
results = schema.search_knowledge.exec('data infrastructure')
memories = schema.recall_memory.exec('deployment options')
history = schema.get_history.exec('sess-1')
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
agent/
├── schema.py        Tables, views, indexes, computed columns, tools, query functions
├── functions.py     UDFs (web_search, assemble_context)
├── app.py           FastAPI server — API + web UI
├── static/
│   └── index.html   Frontend (Tailwind CSS, vanilla JS)
├── pyproject.toml   Dependencies + pxt serve routes
└── README.md
```
