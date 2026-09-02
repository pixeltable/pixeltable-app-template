# Chat agent

Knowledge, memory, and the Anthropic answer are tables and computed columns.
One application file (`app.py`). `POST /api/knowledge` does not need an API key.
`/ask` and `ask()` need `ANTHROPIC_API_KEY`.
Declare (`pxt schema update app.py agent`), Serve (`pxt service update`), Experiment (insert, `/ask`, `pxt dashboard`).

```bash
cd chat-agent
uv sync
uv run pxt schema update app.py agent
uv run pxt service update app.py agent
uv run pxt service list
```

Foreground: `uv run pxt service run app.py agent --port 8000`.
Docker Compose keeps 8000: `docker compose up --build`.

HTTP `/ask` calls `ask()`, which writes user and assistant turns after the answer.

```bash
curl -s -X POST http://localhost:8000/api/knowledge \
  -H "Content-Type: application/json" \
  -d '{"body": "One application file. Insert runs compute.", "title": "intro", "source": "docs"}'

curl -s "http://localhost:8000/api/knowledge/search?query_text=application%20file&limit=5"
```

`/ask` (set `ANTHROPIC_API_KEY` first):

```bash
export ANTHROPIC_API_KEY=sk-...

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

## No HTTP

Apply, then insert and export from Python. Same pattern as [Self-hosting](https://docs.pixeltable.com/howto/deployment/overview).

```bash
uv run pxt schema update app.py agent
```

```python
from pixeltable.io.sql import export_sql

from app import Knowledge

Knowledge.insert(
    [{"body": "One application file. Insert runs compute.", "title": "intro", "source": "docs"}]
)
export_sql(
    Knowledge.select(Knowledge.title, Knowledge.body, Knowledge.uuid),
    "knowledge",
    db_connect_str="sqlite:///agent.db",
    if_exists="replace",
)
```

Cloud:

```bash
pxt db update pxt://org:mydb
pxt secret set pxt://org ANTHROPIC_API_KEY=sk-...
pxt schema update app.py pxt://org:mydb
pxt service update app.py pxt://org:mydb
```

`pxt db update` packs the hosted image and workers; it is not Experiment.
`pxt service run` is local only. Experiment on Cloud is dashboard insert plus `pxt schema diff`.
[Cloud docs](https://docs.pixeltable.com/howto/deployment/cloud).

| Object | Role |
|--------|------|
| `agent.knowledge` | Source documents (`body`, not `text`, so the sentence iterator can own `text`) |
| `agent.sentences` | Sentence chunks + embedding index |
| `agent.conversations` | Chat turns + embedding index |
| `agent.agent` | Prompt to memory/knowledge context to Anthropic to `answer` |

Name the stored text column something other than the iterator output. Do not `base=Knowledge.select(...)` to dodge a `text` / `text_1` clash.
