"""FastAPI backend for the full-stack showcase.

Serves the React frontend (if built) and exposes REST endpoints for:
  - Video upload, list, detail, delete
  - Cross-modal search (text, image, video, audio)
  - Browse (frames, segments, scenes, audio, detections)
  - Dashboard (stats, alerts, activity)

    uv run uvicorn app:app --reload        # dev server
    uv run pxt serve sitewatch             # prod (reads pyproject.toml routes)
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

import pixeltable as pxt

import config
from routers import browse, dashboard, search, videos

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s [%(name)s] %(message)s')
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        pxt.get_table(f'{config.NAMESPACE}.videos')
        logger.info('Connected to Pixeltable schema')
    except Exception:
        logger.warning(
            'Pixeltable schema not initialized. '
            "Run 'python schema.py' first."
        )
    yield


app = FastAPI(
    title='SiteWatch — Full-Stack Showcase',
    description='Video intelligence platform powered by Pixeltable',
    version='1.0.0',
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(videos.router)
app.include_router(search.router)
app.include_router(browse.router)
app.include_router(dashboard.router)


@app.get('/api/health')
def health():
    return {'status': 'ok'}


STATIC_DIR = Path(__file__).resolve().parent / 'static'


@app.get('/{full_path:path}')
def spa_fallback(full_path: str):
    if not STATIC_DIR.is_dir():
        return JSONResponse(
            {'detail': 'Frontend not built. Run: cd frontend && npm run build'},
            status_code=404,
        )
    file_path = STATIC_DIR / full_path
    if file_path.is_file():
        return FileResponse(file_path)
    return FileResponse(STATIC_DIR / 'index.html')


if __name__ == '__main__':
    import uvicorn

    uvicorn.run('app:app', host='0.0.0.0', port=8000, reload=True)
