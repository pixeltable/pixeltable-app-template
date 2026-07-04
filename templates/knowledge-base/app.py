"""Multimodal RAG — FastAPI application.

Uses pixeltable.serving.FastAPIRouter for Pixeltable-native routes.
Custom endpoints for cross-modal search and LLM Q&A.
Run: python app.py
"""

from pathlib import Path

import pixeltable as pxt
import schema
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pixeltable.serving import FastAPIRouter
from pydantic import BaseModel

app = FastAPI(title="Multimodal RAG")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Pixeltable router (handles serialization, file uploads, media URLs) ──

router = FastAPIRouter(prefix="/api", tags=["knowledge-base"])

# Per-modality inserts with file upload
router.add_insert_route(
    schema.documents,
    path="/ingest/document",
    uploadfile_inputs=["doc"],
    outputs=["id"],
    background=True,
)
router.add_insert_route(
    schema.images,
    path="/ingest/image",
    uploadfile_inputs=["image"],
    inputs=["caption"],
    outputs=["id"],
)
router.add_insert_route(
    schema.videos,
    path="/ingest/video",
    uploadfile_inputs=["video"],
    outputs=["id"],
    background=True,
)
router.add_insert_route(
    schema.audio_files,
    path="/ingest/audio",
    uploadfile_inputs=["audio"],
    outputs=["id"],
    background=True,
)

# Per-modality search queries
router.add_query_route(path="/search/documents", query=schema.search_documents, method="post")
router.add_query_route(path="/search/images", query=schema.search_images, method="post")
router.add_query_route(path="/search/video-frames", query=schema.search_video_frames, method="post")

app.include_router(router)

# ── Custom endpoints (cross-modal aggregation, LLM Q&A) ─────────────────


class SearchRequest(BaseModel):
    query: str
    n: int = 20


class AskRequest(BaseModel):
    question: str


@app.post("/api/search")
def search(req: SearchRequest):
    results = schema.search_knowledge(req.query, req.n)
    return {"results": results}


@app.post("/api/ask")
def ask(req: AskRequest):
    return schema.ask_question(req.question)


@app.get("/api/stats")
def stats():
    return {
        "documents": pxt.get_table("kb.documents").count(),
        "images": pxt.get_table("kb.images").count(),
        "videos": pxt.get_table("kb.videos").count(),
        "audio": pxt.get_table("kb.audio_files").count(),
    }


# ── Static UI ────────────────────────────────────────────────────────────

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


def _find_port(default: int = 8000) -> int:
    import os
    import socket

    port = int(os.environ.get("PORT", default))
    while port < default + 100:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", port)) != 0:
                return port
        port += 1
    return default


if __name__ == "__main__":
    port = _find_port()
    print(f"Starting server at http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
