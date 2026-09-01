# Contributing

## Development setup

```bash
git clone https://github.com/pixeltable/pixeltable-starter-kit.git
cd pixeltable-starter-kit
uv sync
```

Apps require Pixeltable from GitHub (PyPI 0.7.2 cannot resolve TableModel `.similarity`) and Python 3.11+. HuggingFace
sentence-transformer embeddings require sentence-transformers 5.6.0+.

## Testing

```bash
uv sync
uv run ruff check video-search/ chat-agent/ tests/
uv run ruff format video-search/ chat-agent/ tests/ --check
uv run python -m pytest tests/ -v
```

Slow checks in `.github/workflows/test.yml`:

- **schema-smoke** (every push/PR): `pytest tests/test_schema.py --run-slow`
- **app-smoke** (weekly + manual dispatch): chat-agent HTTP. Video search skips if no clip is present.

## Apps

`chat-agent/` is the default `uvx pixeltable-new` extract. `video-search/` is `--video`.

Each app needs: `app.py`, `pixeltable.toml` (`[[pixeltable.database]]`),
`pyproject.toml` (`[build-system]` and `[tool.setuptools] py-modules` listing `app`),
`README.md`, `Dockerfile`, `docker-compose.yml`.

Do not add TOML service route tables. Do not add `templates/` or a second
apply path. Tables are declared in `app.py` and applied with `pxt schema update`.

Cloud recipes: [`gallery.json`](gallery.json). Same application file.

`pixeltable-new` fetches `chat-agent/` or `video-search/` from this repo's `main` tarball.
Printed next-steps live in pixeltable-new and need a PyPI release to change.

## Linting

Ruff in root `pyproject.toml`: line-length 120; rules `E, W, F, I, B, C4, UP`;
ignored `E501`, `B008`, `B904`.

## Releasing pixeltable-new

See [`pixeltable-new/CONTRIBUTING.md`](https://github.com/pixeltable/pixeltable-new/blob/main/CONTRIBUTING.md).
