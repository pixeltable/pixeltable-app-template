# Contributing

## Development setup

```bash
git clone https://github.com/pixeltable/pixeltable-starter-kit.git
cd pixeltable-starter-kit
uv sync
```

Patterns require Pixeltable 0.6.5+ and Python 3.11+. HuggingFace
sentence-transformer embeddings require sentence-transformers 5.6.0+.

## Testing

```bash
uv sync
uv run ruff check serving/ batch/ examples/ tests/
uv run ruff format serving/ batch/ examples/ tests/ --check
uv run python -m pytest tests/ -v
```

Slow checks in `.github/workflows/test.yml`:

- **schema-smoke** (every push/PR): `pytest tests/test_schema.py --run-slow`
- **app-smoke** (weekly + manual dispatch): serving HTTP + batch `pipeline.py`

## Patterns

`serving/` is the default `uvx pixeltable-new` extract. `batch/` is `--batch`.

Each pattern needs: `app.py`, `pixeltable.toml` (`[[pixeltable.database]]`),
`pyproject.toml` (`[build-system]` and `[tool.setuptools] py-modules` listing `app`
for serving), `README.md`.

Do not add TOML service route tables. Do not add `templates/` or a second
apply path. Tables are declared in `app.py` and applied with `pxt schema update`.

`examples/` are Cloud gallery apps (`gallery.json`). Same `app.py` contract.
`pixeltable-new` does not copy them. Each example README names its catalog TARGET.

`pixeltable-new` fetches `serving/` or `batch/` from this repo's `main` tarball.
Printed next-steps live in pixeltable-new and need a PyPI release to change.

## Linting

Ruff in root `pyproject.toml`: line-length 120; rules `E, W, F, I, B, C4, UP`;
ignored `E501`, `B008`, `B904`.

## Releasing pixeltable-new

See [`pixeltable-new/CONTRIBUTING.md`](https://github.com/pixeltable/pixeltable-new/blob/main/CONTRIBUTING.md).
