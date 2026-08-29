# API Backend

FastAPI plus Pixeltable. This pattern keeps a hand-written FastAPI `main.py` and mounts Pixeltable routers.

`pixeltable.toml` marks this directory as a project root.

## Mount a FastAPIRouter from the application file

Declare tables and routes in `app.py`, apply them, then include the router:

```python
from fastapi import FastAPI
from pixeltable.serving import FastAPIRouter

# from app import api   # FastAPIRouter declared next to TableModel classes
from routers import agent, data, search

app = FastAPI()
app.include_router(data.router)
app.include_router(search.router)
app.include_router(agent.router)
```

For a new app, put `TableModel` classes and the `FastAPIRouter` in one application file:

```python
from pixeltable.serving import FastAPIRouter

api = FastAPIRouter(name='api', prefix='/api')
api.add_insert_route(Documents, path='/documents', inputs=[Documents.title])
```

```bash
pxt schema update app.py my_app
# then: app.include_router(api) in main.py, or pxt service update app.py my_app
```

This repo's `main.py` still imports `setup_pixeltable` (create_table) and the routers under `routers/`. That is Approach 2: an existing FastAPI app. Do not run `python schema.py` as an apply step.

## Run

```bash
uv sync
python main.py          # http://localhost:8000
```

See the [root README](../README.md) for the frontend and deploy paths.
