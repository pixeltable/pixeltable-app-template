# Chat agent

Knowledge, memory, and the Anthropic answer are tables and computed columns.
One application file (`app.py`). `POST /api/knowledge` does not need an API key.
`/ask` and `ask()` need `ANTHROPIC_API_KEY`.
Declare (`pxt schema update app.py agent`), Experiment (insert, `/ask`, `pxt dashboard`), Serve (`pxt service update`).

```bash
export ANTHROPIC_API_KEY=sk-...   # before the first pxt command -- see below
cd chat-agent
uv sync
uv run pxt schema update app.py agent
uv run pxt service update app.py agent
uv run pxt service list
```

The export has to come first. `pxt schema update` starts the Pixeltable daemon, `pxt service update` spawns the
service from that daemon, and the service inherits the daemon's environment -- so a key exported afterwards
never reaches `/ask`. Re-running `pxt service update` does not fix it either: the plan is already in agreement,
so nothing respawns. If you get this wrong:

```bash
uv run pxt daemon restart
uv run pxt service stop agent
uv run pxt service update app.py agent
```

`uv run pxt config --section anthropic` reports what the daemon actually resolved.

HTTP `/ask` inserts an agent row, returns `answer`, and writes user and assistant turns.

```bash
curl -s -X POST http://127.0.0.1:<port>/api/knowledge \
  -H "Content-Type: application/json" \
  -d '{"body": "Pixeltable is a unified backend: one application file, tables, and insert runs compute.", "title": "intro", "source": "docs"}'

curl -s "http://127.0.0.1:<port>/api/knowledge/search?query_text=application%20file&limit=5"
```

`/ask` needs the key you exported above. `uv run pxt service list` prints the port.

```bash
curl -s -X POST http://127.0.0.1:<port>/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is Pixeltable?",
    "conversation_id": "demo",
    "system_prompt": "You are a helpful assistant. Use the knowledge and memory context. Be concise.",
    "max_tokens": 1024,
    "temperature": 0.7
  }'

uv run python -c "import app; print(app.ask('What is Pixeltable?', conversation_id='demo'))"

curl -s "http://127.0.0.1:<port>/api/memory/search?query_text=Pixeltable&limit=5"
```

## Without HTTP

Apply, then insert from Python. Same pattern as [Self-hosting](https://docs.pixeltable.com/howto/deployment/overview).

```bash
uv run pxt schema update app.py agent
```

```python
import pixeltable as pxt

knowledge = pxt.get_table("agent.knowledge")
knowledge.insert(
    [{"body": "Pixeltable is a unified backend: one application file, tables, and insert runs compute.", "title": "intro", "source": "docs"}]
)
```

## Same file, hosted

```bash
uv run pxt db update pxt://org:mydb
uv run pxt secret set pxt://org ANTHROPIC_API_KEY=sk-...
uv run pxt schema update app.py pxt://org:mydb
uv run pxt service update app.py pxt://org:mydb
```

Experiment on Cloud is dashboard insert plus `pxt schema diff`.
[Cloud docs](https://docs.pixeltable.com/howto/deployment/cloud).

## Container

`docker compose up --build` serves on port 8000. Export `ANTHROPIC_API_KEY` in the shell that runs
it, or `/ask` returns an error while the other routes work.

| Object | Role |
|--------|------|
| `agent.knowledge` | Source documents (`body`, not `text`, so the sentence iterator can own `text`) |
| `agent.sentences` | Sentence chunks + embedding index |
| `agent.conversations` | Chat turns + embedding index |
| `agent.agent` | Prompt to memory/knowledge context to Anthropic to `answer` |

Name the stored text column something other than the iterator output. Do not `base=Knowledge.select(...)` to dodge a `text` / `text_1` clash.
