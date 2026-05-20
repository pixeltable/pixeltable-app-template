"""Audio Intelligence — FastAPI application.

Uses pixeltable.serving.FastAPIRouter for all Pixeltable-native routes.
Run: python app.py
"""

from pathlib import Path

import schema
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pixeltable.serving import FastAPIRouter

app = FastAPI(title="Audio Intelligence")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Pixeltable router (handles serialization, file uploads, media URLs) ──

router = FastAPIRouter(prefix="/api", tags=["audio-intel"])

router.add_insert_route(
    schema.audio_files,
    path="/upload",
    uploadfile_inputs=["audio"],
    inputs=["title", "source"],
    outputs=["uuid"],
    background=True,
)

router.add_query_route(path="/recordings", query=schema.list_recordings, method="get")

if schema.HAVE_OPENAI:
    router.add_query_route(path="/transcript", query=schema.get_transcript, method="get")
    router.add_query_route(path="/summary", query=schema.get_summary, method="get")
    router.add_query_route(path="/search", query=schema.search_transcripts, method="post")
    router.add_query_route(path="/search-in", query=schema.search_in_recording, method="post")

app.include_router(router)

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
