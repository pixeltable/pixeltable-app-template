import logging
from pathlib import Path

import config
import setup_pixeltable  # noqa: F401 — triggers schema init on first import
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from routers import agent, data, search

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

app = FastAPI(title="Pixeltable Starter Kit", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(data.router)
app.include_router(search.router)
app.include_router(agent.router)

STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    if not STATIC_DIR.is_dir():
        return JSONResponse(
            {"detail": "Frontend not built. Run: cd frontend && npm run build"},
            status_code=404,
        )
    requested = (STATIC_DIR / full_path).resolve()
    # Containment guard: reject paths that escape STATIC_DIR (e.g. "../../etc/passwd").
    if requested.is_relative_to(STATIC_DIR) and requested.is_file():
        return FileResponse(requested)
    return FileResponse(STATIC_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_excludes=["data/*", "*.log"],
    )
