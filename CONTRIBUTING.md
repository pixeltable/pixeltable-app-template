# Contributing

## Development Setup

```bash
git clone https://github.com/pixeltable/pixeltable-starter-kit.git
cd pixeltable-starter-kit
uv sync                            # installs dev deps (pytest, ruff)
```

All patterns and templates require **Pixeltable 0.6.5+** and **Python 3.11+**. Those that use HuggingFace sentence-transformer embeddings also require **sentence-transformers 5.6.0+**; the exceptions are `full-stack-showcase` (Gemini embeddings) and `image-dataset` (CLIP), which don't need it.

## Testing

```bash
uv sync
uv run ruff check backend/ serving/ batch/ templates/ tests/
uv run ruff format backend/ serving/ batch/ templates/ tests/ --check
uv run python -m pytest tests/ -v
cd frontend && npm ci && npm run build
```

Slow checks run in CI via `.github/workflows/test.yml`:

- **schema-smoke** (every push/PR): `pytest tests/test_schema.py --run-slow`
- **app-smoke** (weekly + manual dispatch): starts each pattern/template server and verifies HTTP responses

## Template Development

### Two categories

UI templates (knowledge-base, chat-agent, audio-transcription, full-stack-showcase):
- `app.py` does `import schema` which triggers schema init on import
- `python app.py` is the **single entry point**
- Port auto-detection: probes from 8000 upward, respects `PORT` env var
- Do not document the retired TOML serving CLI

Application-file templates (video-search, media-indexing, image-dataset, and `serving/`):
- `app.py` declares `TableModel` classes and a `FastAPIRouter`
- Apply: `pxt schema update app.py TARGET`
- Serve: `pxt service update app.py TARGET` or `pxt service run app.py TARGET`
- Indexes on the model: `__indexes__ = [pxt.EmbeddingIndex(...)]`
- `TARGET` is a catalog directory, not a folder on disk

### Required files

Every template must have: `app.py` (or `schema.py` + serving `app.py` for UI templates), `pixeltable.toml` (`[[pixeltable.database]]`), `pyproject.toml` (with `[build-system]` and `[tool.setuptools] py-modules`), `README.md`.

Do not add TOML service route tables. Routes belong on FastAPIRouter in app.py.

### How scaffolding works

`pixeltable-new` fetches `templates/<name>/` from this repo's `main` branch as a tarball. Changes pushed to `main` are **immediately live** for anyone who scaffolds. No publish step needed for template content. The CLI's printed next-steps are in `pixeltable-new`'s `TEMPLATE_NEXT_STEPS` dict and require a PyPI release to update.

### Checklist for new templates

1. Create `templates/<name>/` with `app.py`, `pixeltable.toml`, `pyproject.toml`, `README.md`
2. Add `[build-system]` and `[tool.setuptools] py-modules` listing `app`
3. Declare routes on `FastAPIRouter` in `app.py`
4. Add the template to `tests/conftest.py` (`TEMPLATES` and `EXPECTED_TEMPLATE_FILES`)
5. Add the template to `pixeltable-new`'s `TEMPLATES`, `TEMPLATE_DESCRIPTIONS`, and `TEMPLATE_NEXT_STEPS`
6. Run `uv run python -m pytest tests/ -v` to verify
7. Update root `README.md` template table

## Linting

Ruff is configured in root `pyproject.toml` under `[tool.ruff]`:

- `line-length = 120`
- Rules: `E, W, F, I, B, C4, UP`
- Ignored: `E501` (line length), `B008` (FastAPI `File(...)` in defaults), `B904` (FastAPI `raise HTTPException`)

## Releasing pixeltable-new

See [`pixeltable-new/CONTRIBUTING.md`](https://github.com/pixeltable/pixeltable-new/blob/main/CONTRIBUTING.md).
