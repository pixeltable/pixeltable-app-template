# Pixeltable Starter Kit

Two apps. Each is one application file (`app.py`).
Declare, Experiment, Serve: `pxt schema update`, then `pxt service update`, then insert, `/ask`, or `pxt dashboard`.

**Export your API keys before the first `pxt` command.** That first command starts the Pixeltable daemon, and
the service it later spawns inherits the daemon's environment -- so a key exported afterwards is invisible to
`/ask`, and re-running `pxt service update` will not pick it up. Recovery is
`pxt daemon restart`, then `pxt service stop agent`, then `pxt service update app.py agent`.

## Chat agent

```bash
export ANTHROPIC_API_KEY=sk-...        # before the first pxt command; /ask needs it
uvx pixeltable-new myapp
cd myapp && uv sync
uv run pxt schema update app.py agent
uv run pxt service update app.py agent
uv run pxt service list
```

Already cloned: `cd chat-agent` instead of `uvx pixeltable-new`, then the same `uv sync` and `pxt` commands.

```bash
curl -s -X POST http://127.0.0.1:<port>/api/knowledge \
  -H "Content-Type: application/json" \
  -d '{"body": "Pixeltable is a unified backend: one application file, tables, and insert runs compute.", "title": "intro", "source": "docs"}'
```

`POST /api/knowledge` works without a key -- embeddings run locally. Only `/ask` needs `ANTHROPIC_API_KEY`.

## Video search

```bash
uvx pixeltable-new myapp --video
cd myapp && uv sync
uv run pxt schema update app.py videointel
uv run pxt service update app.py videointel
uv run pxt service list
```

Already cloned: `cd video-search` instead of `uvx pixeltable-new --video`.

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

Already have FastAPI: apply the file, then `app.include_router(api)` on the router in `app.py`.

## Same file, hosted

```bash
uv run pxt db update pxt://org:mydb
uv run pxt schema update app.py pxt://org:mydb
uv run pxt service update app.py pxt://org:mydb
```

Chat agent `/ask` also needs `pxt secret set pxt://org ANTHROPIC_API_KEY=sk-...` before schema update.
`pxt db update` packs the hosted image and workers; it is not Experiment.
`pxt service run` is local only. Experiment on Cloud is dashboard insert plus `pxt schema diff`.
[Cloud](https://docs.pixeltable.com/howto/deployment/cloud).

## Without HTTP

Apply, then insert from Python or open `pxt dashboard`. [Self-hosting](https://docs.pixeltable.com/howto/deployment/overview).

## For agents

Emit `TableModel` classes and a `FastAPIRouter` in `app.py`. Indexes go on `__indexes__`.
Run `uv run pxt schema diff app.py agent` (or `videointel`). Exit 0 means in sync. Exit 2 means pending (`--json` is the plan).
Exit 1 is an error that names the file, declaration, or key. Then `pxt schema update`.
Do not emit a sequence of table-create or column-add calls. Destructive ops need `--allow-destructive`.

Layout and tests: [AGENTS.md](AGENTS.md).
Skill: `npx skills add pixeltable/pixeltable-skill`.

Python 3.11+. `uv sync` installs `pixeltable[serve]>=0.7.5`.

## Resources

- [Quickstart](https://docs.pixeltable.com/overview/quick-start) · [How it works](https://docs.pixeltable.com/overview/how-it-works)
- [Self-hosting](https://docs.pixeltable.com/howto/deployment/overview) · [Cloud](https://docs.pixeltable.com/howto/deployment/cloud) · [HTTP serving](https://docs.pixeltable.com/howto/deployment/serving)
- [pixeltable-new](https://github.com/pixeltable/pixeltable-new) · [pixeltable-skill](https://github.com/pixeltable/pixeltable-skill)

## License

Apache 2.0
