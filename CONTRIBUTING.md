# Contributing

## Development Setup

```bash
git clone https://github.com/pixeltable/pixeltable-starter-kit.git
cd pixeltable-starter-kit
uv sync                            # installs dev deps (pytest, ruff)
```

## Testing

```bash
uv run ruff check tests/ templates/          # lint
uv run ruff format tests/ templates/ --check # format check
uv run python -m pytest tests/ -v            # full suite (~121 tests)
```

Tests live in `tests/` and cover:

- **Structure** (`test_structure.py`): file existence, Python syntax, documentation, anti-pattern guard
- **Config** (`test_config.py`): TOML parsing, `[build-system]`, `pxt serve` routes, colon-separated query format
- **Templates** (`test_templates.py`): schema functions exist, TOML routes reference real functions, namespace consistency
- **Schema** (`test_schema.py`): smoke-import of `schema.py` (marked `slow`, skipped by default)

CI runs automatically on push/PR via `.github/workflows/test.yml`.

## Template Development

### Two categories

Templates with `app.py` (knowledge-base, chat-agent, audio-transcription, full-stack-showcase):
- `app.py` does `import schema` which triggers schema init on import
- `python app.py` is the **single entry point** -- no separate `schema.py` step
- Port auto-detection: probes from 8000 upward, respects `PORT` env var
- `pxt serve` routes in `pyproject.toml` are an API-only alternative (same port, don't run both)
- `schema.py __main__` should print: `Schema initialized. Run: python app.py`

Templates without `app.py` (video-search, media-indexing, image-dataset):
- Entry point: `python schema.py` then `pxt serve <name>`
- `schema.py __main__` should print: `Schema initialized. Run: pxt serve <name>`

### Required files

Every template must have: `schema.py`, `pyproject.toml` (with `[build-system]`, `[tool.setuptools] py-modules`, and `[[tool.pixeltable.service]]`).

### How scaffolding works

`pixeltable-new` fetches `templates/<name>/` from this repo's `main` branch as a tarball. Changes pushed to `main` are **immediately live** for anyone who scaffolds. No publish step needed for template content. The CLI's printed next-steps are in `pixeltable-new`'s `TEMPLATE_NEXT_STEPS` dict and require a PyPI release to update.

### Checklist for new templates

1. Create `templates/<name>/` with `schema.py`, `pyproject.toml`, `README.md`
2. Add `[build-system]` and `[tool.setuptools] py-modules` to `pyproject.toml`
3. Add `[[tool.pixeltable.service]]` with routes
4. Query routes use colon format: `query = "schema:function_name"`
5. Add the template to `tests/conftest.py` (`TEMPLATES` and `EXPECTED_TEMPLATE_FILES`)
6. Add the template to `pixeltable-new`'s `TEMPLATES`, `TEMPLATE_DESCRIPTIONS`, and `TEMPLATE_NEXT_STEPS`
7. Run `uv run python -m pytest tests/ -v` to verify
8. Update root `README.md` template table

## Linting

Ruff is configured in `ruff.toml` (takes precedence over `pyproject.toml`):

- `line-length = 120`
- Rules: `E, W, F, I, B, C4, UP`
- Ignored: `E501` (line length), `B008` (FastAPI `File(...)` in defaults), `B904` (FastAPI `raise HTTPException`)

## Releasing pixeltable-new

See [`pixeltable-new/CONTRIBUTING.md`](https://github.com/pixeltable/pixeltable-new/blob/main/CONTRIBUTING.md).
