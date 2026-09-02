# Pixeltable Starter Kit

Two apps. Each is one application file (`app.py`).
Declare, Experiment, Serve: `pxt schema update`, then `pxt service update`, then insert, `/ask`, or `pxt dashboard`.

## Video search

```bash
cd video-search
uv sync
pxt schema update app.py videointel
pxt service update app.py videointel
pxt service list
```

```bash
curl -s -X POST http://127.0.0.1:<port>/api/ingest \
  -F "video=@/path/to/clip.mp4" \
  -F "title=demo"

curl -s -X POST http://127.0.0.1:<port>/api/ingest/image \
  -F "image=@/path/to/photo.jpg" \
  -F "label=demo" \
  -F "source_id=api-001"
```

Video ingest is a background job. Poll `job_url` from the insert response.

## Chat agent

```bash
cd chat-agent
uv sync
pxt schema update app.py agent
pxt service update app.py agent
pxt service list
```

```bash
curl -s -X POST http://127.0.0.1:<port>/api/knowledge \
  -H "Content-Type: application/json" \
  -d '{"body": "One application file. Insert runs compute.", "title": "intro", "source": "docs"}'
```

`POST /api/knowledge` works without a key. `/ask` needs `ANTHROPIC_API_KEY`.

Scaffold with `uvx pixeltable-new myapp` (chat agent) or `uvx pixeltable-new myapp --video`.

Already have FastAPI: apply the file, then `app.include_router(api)` on the router in `app.py`.

## Same file, hosted

```bash
pxt db update pxt://org:mydb
pxt schema update app.py pxt://org:mydb
pxt service update app.py pxt://org:mydb
```

`pxt db update` packs the hosted image and workers; it is not Experiment.
`pxt service run` is local only. Experiment on Cloud is dashboard insert plus `pxt schema diff`.
[Cloud](https://docs.pixeltable.com/howto/deployment/cloud).

## No HTTP

Apply chat-agent, then insert and `export_sql` from Python. Snippet: [`chat-agent/README.md`](chat-agent/README.md).

## For agents

Emit `TableModel` classes and a `FastAPIRouter` in `app.py`. Indexes go on `__indexes__`.
Run `pxt schema diff app.py agent` (or `videointel`). Exit 0 means in sync. Exit 2 means pending (`--json` is the plan).
Exit 1 is an error that names the file, declaration, or key. Then `pxt schema update`.
Do not emit a sequence of table-create or column-add calls. Destructive ops need `--allow-destructive`.

Layout and tests: [AGENTS.md](AGENTS.md).
Skill: `npx skills add pixeltable/pixeltable-skill`.

Python 3.11+. `uv sync` installs `pixeltable[serve]>=0.7.4`.

## Resources

- [Quickstart](https://docs.pixeltable.com/overview/quick-start) · [How it works](https://docs.pixeltable.com/overview/how-it-works)
- [Self-hosting](https://docs.pixeltable.com/howto/deployment/overview) · [Cloud](https://docs.pixeltable.com/howto/deployment/cloud) · [HTTP serving](https://docs.pixeltable.com/howto/deployment/serving)
- [pixeltable-new](https://github.com/pixeltable/pixeltable-new) · [pixeltable-skill](https://github.com/pixeltable/pixeltable-skill)

## License

Apache 2.0
