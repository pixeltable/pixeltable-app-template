# AGENTS.md

Instructions for AI coding agents working in the Pixeltable Starter Kit.

## Product contract

Apps are one Python file (`app.py`): `TableModel` classes and a `FastAPIRouter`.
Apply with `pxt schema update`. Serve locally with `pxt service update` or
`pxt service run`. Indexes belong on the model (`__indexes__`). Routes live
on `FastAPIRouter`. No TOML route tables.

```bash
uvx pixeltable-new myapp
cd myapp && uv sync
pxt schema update app.py pipeline
pxt service update app.py pipeline
```

`pipeline` is a catalog directory, not a folder on disk. Advertised patterns
apply via `pxt schema update` only.

## Layout

```
serving/     Default. TableModel + FastAPIRouter. TARGET pipeline.
batch/       No HTTP. Same models, then python pipeline.py.
examples/    Cloud gallery DAGs (video-search, chat-agent). Not copied by uvx.
gallery.json Cloud recipe manifest. Fetch URL: /gallery.json on main.
tests/       Structure and config. Schema smoke: --run-slow.
```

Do not add `templates/`, `backend/`, or a PaaS `deploy/` zoo. Do not extract
`examples/` from `pixeltable-new`. New verticals: edit `app.py` or add a folder
under `examples/` with the same apply path and a `gallery.json` row.

## Extend serving

1. Add a `TableModel` in `serving/app.py`.
2. Put indexes on the class (`__indexes__`).
3. Register routes on the existing `FastAPIRouter`.
4. Run `pxt schema update app.py pipeline`.

Annotation is a stored column. Assignment is a computed column.
Primary key is `pxt.Column(..., primary_key=True)`, not a bare typed field.

## Testing

```bash
uv sync
uv run ruff check serving/ batch/ examples/ tests/
uv run ruff format serving/ batch/ examples/ tests/ --check
uv run python -m pytest tests/ -v
```

Schema import smoke (needs Pixeltable in each pattern venv):

```bash
cd serving && uv sync && cd ../batch && uv sync && cd ..
uv run python -m pytest tests/test_schema.py -v --run-slow
```

## Files to read first

1. `serving/app.py`
2. `serving/README.md`
3. [pixeltable/pixeltable AGENTS.md](https://github.com/pixeltable/pixeltable/blob/main/AGENTS.md)
4. [pixeltable-skill](https://github.com/pixeltable/pixeltable-skill)
