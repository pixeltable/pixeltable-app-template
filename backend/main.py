import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import pixeltable as pxt

from routers import data, search, agent

load_dotenv(override=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        pxt.get_table("app.agent")
        logger.info("Connected to Pixeltable schema")
    except Exception:
        logger.warning(
            "Pixeltable schema not initialized. "
            "Run 'python setup_pixeltable.py' first. "
            "The server will start but API calls will fail."
        )
    yield


app = FastAPI(
    title="Pixeltable App Template",
    description="Full-stack starter app powered by Pixeltable",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data.router)
app.include_router(search.router)
app.include_router(agent.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serve frontend static build (production)
STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.is_dir():
    from fastapi.responses import FileResponse

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")

    logger.info(f"Serving frontend from {STATIC_DIR}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_excludes=["data/*", "*.log"],
        loop="asyncio",
    )
