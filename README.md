# Pixeltable Starter Kit

One application file (`app.py`) declares tables, computed columns, indexes, and HTTP routes.
`pxt schema update` applies the tables. `pxt service` serves the `FastAPIRouter` in the same file.

Python 3.11+. Pixeltable 0.6.5+.

```bash
uvx pixeltable-new myapp
cd myapp && uv sync
pxt schema update app.py pipeline
pxt service update app.py pipeline
```

`pipeline` is a catalog directory, not a folder on disk. `pxt service list` prints the URL.
OpenAPI is at `/docs`. Routes live on a `FastAPIRouter` in `app.py`.

A project root is `pixeltable.toml` (or `pyproject.toml` with `[tool.pixeltable]`). The
scaffold writes one. If you copied files by hand, run `pxt init` first.

Need HTTP? That is the default (`serving/`). No HTTP? `uvx pixeltable-new myapp --batch`.
Video frames and an agent-as-table live in [`examples/`](examples/) (same apply path;
not copied by `uvx`). Cloud reads [`gallery.json`](gallery.json). Other apps are written
into `app.py` by an agent with the [Pixeltable skill](https://github.com/pixeltable/pixeltable-skill).

## Serving

[`serving/`](serving/) is what `uvx pixeltable-new myapp` copies.

```bash
cd serving
uv sync
uv run pxt schema update app.py pipeline
uv run pxt service update app.py pipeline
uv run pxt service list
```

Foreground / containers: `uv run pxt service run app.py pipeline --port 8000`.
Docker: `docker compose up --build` in `serving/`.

Hosted catalog: `pxt schema update app.py pxt://org:db`. `pxt service` is local-only.
See [`serving/deploy/pixeltable-cloud/`](serving/deploy/pixeltable-cloud/).

Already have FastAPI? Apply the file, then `app.include_router(api)` on the router
declared in `app.py`. Call `pxt.get_table()` inside custom handlers.

## Batch

[`batch/`](batch/) is ingest, compute, export, exit. No HTTP.

```bash
cd batch
uv sync
uv run pxt schema update app.py pipeline
uv run python pipeline.py
```

## Examples

[`examples/`](examples/) are extra DAGs for Cloud recipes: video search (`frame_iterator` +
CLIP) and a chat agent (query functions as computed columns). Copy the folder, then the
same CLI as serving, with the TARGET in that example's README (`videointel` or `agent`).

## Resources

- [Docs](https://docs.pixeltable.com/) · [HTTP serving](https://docs.pixeltable.com/howto/deployment/serving)
- [pixeltable-new](https://github.com/pixeltable/pixeltable-new) · [pixeltable-skill](https://github.com/pixeltable/pixeltable-skill)
- [AGENTS.md](AGENTS.md) for this repo

## License

Apache 2.0
