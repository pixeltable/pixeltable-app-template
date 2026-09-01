# AGENTS.md

Instructions for AI coding agents working in the Pixeltable Starter Kit.

## Apps

Apps are one Python file (`app.py`): `TableModel` classes and a `FastAPIRouter`.
Apply with `pxt schema update`. Serve with `pxt service update` or `pxt service run`.
Indexes belong on the model (`__indexes__`). Routes live on `FastAPIRouter`. No TOML route tables.
Already have FastAPI? `app.include_router(...)` on the router in `app.py`.

Same file on Cloud: `pxt db create pxt://org:mydb`, then
`pxt secret set pxt://org KEY=...`, then `pxt schema update app.py pxt://org:mydb`.
Then `t = pxt.get_table('pxt://org:mydb/docs')`.
`pxt schema update` applies tables to the hosted catalog. It does not start HTTP.
`pxt service` binds to the local catalog. A hosted URI is refused.

```bash
uvx pixeltable-new myapp
cd myapp && uv sync
pxt schema update app.py agent
pxt service update app.py agent
```

`agent` and `videointel` are catalog directories, not folders on disk.
Video: `uvx pixeltable-new myapp --video`, then TARGET `videointel`.

## Layout

```
video-search/   Frames, CLIP, images. TARGET videointel. uvx --video
chat-agent/     Knowledge, memory, LLM. TARGET agent. uvx default
gallery.json    Cloud recipe manifest. Fetch URL: /gallery.json on main.
tests/          Structure and config. Schema smoke: --run-slow.
```

Do not add `templates/`, `backend/`, `serving/`, `batch/`, or a PaaS `deploy/` zoo.
New verticals: edit `app.py` or add a folder next to these two with the same apply path and a `gallery.json` row.

## Extend an app

1. Add a `TableModel` in that app's `app.py`.
2. Put indexes on the class (`__indexes__`).
3. Register routes on the existing `FastAPIRouter`.
4. Run `pxt schema update app.py agent` (or `videointel`).

Annotation is a stored column. Assignment is a computed column.
Primary key is `pxt.Column(..., primary_key=True)`, not a bare typed field.

## Testing

```bash
uv sync
uv run ruff check video-search/ chat-agent/ tests/
uv run ruff format video-search/ chat-agent/ tests/ --check
uv run python -m pytest tests/ -v
```

Schema import smoke (needs Pixeltable in each app venv):

```bash
cd chat-agent && uv sync && cd ../video-search && uv sync && cd ..
uv run python -m pytest tests/test_schema.py -v --run-slow
```

## Files to read first

1. `chat-agent/app.py`
2. `chat-agent/README.md`
3. `video-search/app.py`
4. [pixeltable/pixeltable AGENTS.md](https://github.com/pixeltable/pixeltable/blob/main/AGENTS.md)
5. [pixeltable-skill](https://github.com/pixeltable/pixeltable-skill)
