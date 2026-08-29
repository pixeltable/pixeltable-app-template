# Chat agent

The agent is a table: knowledge, memory, and the Anthropic answer are computed columns.
This is not what `uvx pixeltable-new` copies. Same apply path as `serving/`.
Requires `ANTHROPIC_API_KEY`.

```bash
cd examples/chat-agent
uv sync
export ANTHROPIC_API_KEY=sk-...
uv run pxt schema update app.py agent
uv run pxt service update app.py agent
uv run pxt service list
```

Foreground: `uv run pxt service run app.py agent --port 8000`.
`agent` is a catalog directory, not a folder on disk.

HTTP `/ask` returns `uuid` and `answer`. It does not write conversation memory.
`ask()` in `app.py` writes user and assistant turns after the answer.

```bash
curl -s -X POST http://localhost:8000/api/knowledge \
  -H "Content-Type: application/json" \
  -d '{"body": "Pixeltable is declarative multimodal data infrastructure.", "title": "intro", "source": "docs"}'

curl -s -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is Pixeltable?",
    "conversation_id": "demo",
    "system_prompt": "You are a helpful assistant. Use the knowledge and memory context. Be concise.",
    "max_tokens": 1024,
    "temperature": 0.7
  }'

uv run python -c "import app; print(app.ask('What is Pixeltable?', conversation_id='demo'))"

curl -s "http://localhost:8000/api/memory/search?query_text=Pixeltable&limit=5"
```

Hosted catalog: `pxt schema update app.py pxt://org:db`. `pxt service` is local-only.

| Object | Role |
|--------|------|
| `agent.knowledge` | Source documents (`body`, not `text`, so the sentence iterator can own `text`) |
| `agent.sentences` | Sentence chunks + embedding index |
| `agent.conversations` | Chat turns + embedding index |
| `agent.agent` | Prompt → memory/knowledge context → Anthropic → `answer` |

Name the stored text column something other than the iterator output. Do not `base=Knowledge.select(...)` to dodge a `text` / `text_1` clash.
