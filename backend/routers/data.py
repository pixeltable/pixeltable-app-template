"""Data pipeline endpoints: upload, list, delete, chunks, frames, transcription."""
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile, File
import pixeltable as pxt

import config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/data", tags=["data"])

UPLOAD_DIR = Path(config.UPLOAD_FOLDER)
UPLOAD_DIR.mkdir(exist_ok=True)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi"}


def _classify_file(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"
    return "document"


TABLE_PATHS = {
    "document": f"{config.APP_NAMESPACE}.documents",
    "image": f"{config.APP_NAMESPACE}.images",
    "video": f"{config.APP_NAMESPACE}.videos",
}


# ── Upload ────────────────────────────────────────────────────────────────────

@router.post("/upload", status_code=201)
def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename")

    ext = Path(file.filename).suffix.lower().lstrip(".")
    if ext not in config.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: .{ext}")

    ts = int(datetime.now().timestamp() * 1000)
    safe_name = f"{ts}_{file.filename}"
    file_path = UPLOAD_DIR / safe_name

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    media_type = _classify_file(file.filename)
    table = pxt.get_table(TABLE_PATHS[media_type])

    current_ts = datetime.now()
    table.insert([{
        media_type: str(file_path),
        "timestamp": current_ts,
        "user_id": config.DEFAULT_USER_ID,
    }])

    # Retrieve the auto-generated uuid7() primary key
    rows = list(
        table.where(
            (table.user_id == config.DEFAULT_USER_ID) & (table.timestamp == current_ts)
        )
        .select(table.uuid)
        .limit(1)
        .collect()
    )
    file_uuid = str(rows[0]["uuid"]) if rows else "unknown"

    return {
        "message": f"Uploaded {media_type}",
        "filename": file.filename,
        "uuid": file_uuid,
        "type": media_type,
    }


# ── List files ────────────────────────────────────────────────────────────────

@router.get("/files")
def list_files():
    user_id = config.DEFAULT_USER_ID
    result: dict = {"documents": [], "images": [], "videos": []}

    try:
        docs = pxt.get_table(TABLE_PATHS["document"])
        result["documents"] = list(
            docs.where(docs.user_id == user_id)
            .select(uuid=docs.uuid, name=docs.document, timestamp=docs.timestamp)
            .order_by(docs.timestamp, asc=False)
            .collect()
        )
        for d in result["documents"]:
            d["uuid"] = str(d.get("uuid", ""))
            d["name"] = os.path.basename(str(d.get("name", "")))
            if isinstance(d.get("timestamp"), datetime):
                d["timestamp"] = d["timestamp"].isoformat()
    except Exception as e:
        logger.warning(f"Could not list documents: {e}")

    try:
        imgs = pxt.get_table(TABLE_PATHS["image"])
        result["images"] = list(
            imgs.where(imgs.user_id == user_id)
            .select(
                uuid=imgs.uuid,
                name=imgs.image,
                thumbnail=imgs.thumbnail,
                timestamp=imgs.timestamp,
            )
            .order_by(imgs.timestamp, asc=False)
            .collect()
        )
        for d in result["images"]:
            raw = d.get("name")
            d["uuid"] = str(d.get("uuid", ""))
            d["name"] = os.path.basename(getattr(raw, "filename", "") or "")
            if isinstance(d.get("timestamp"), datetime):
                d["timestamp"] = d["timestamp"].isoformat()
    except Exception as e:
        logger.warning(f"Could not list images: {e}")

    try:
        vids = pxt.get_table(TABLE_PATHS["video"])
        result["videos"] = list(
            vids.where(vids.user_id == user_id)
            .select(uuid=vids.uuid, name=vids.video, timestamp=vids.timestamp)
            .order_by(vids.timestamp, asc=False)
            .collect()
        )
        for d in result["videos"]:
            d["uuid"] = str(d.get("uuid", ""))
            d["name"] = os.path.basename(str(d.get("name", "")))
            if isinstance(d.get("timestamp"), datetime):
                d["timestamp"] = d["timestamp"].isoformat()
    except Exception as e:
        logger.warning(f"Could not list videos: {e}")

    return result


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/files/{file_uuid}/{file_type}")
def delete_file(file_uuid: str, file_type: str):
    if file_type not in TABLE_PATHS:
        raise HTTPException(status_code=400, detail=f"Unknown type: {file_type}")

    table = pxt.get_table(TABLE_PATHS[file_type])
    status = table.delete(
        where=(table.uuid == UUID(file_uuid)) & (table.user_id == config.DEFAULT_USER_ID)
    )
    return {"message": "Deleted", "num_deleted": status.num_rows}


# ── Document chunks ───────────────────────────────────────────────────────────

@router.get("/chunks/{file_uuid}")
def get_chunks(file_uuid: str):
    try:
        chunks = pxt.get_table(f"{config.APP_NAMESPACE}.chunks")
        rows = list(
            chunks.where(chunks.uuid == UUID(file_uuid))
            .select(text=chunks.text, title=chunks.title, heading=chunks.heading, page=chunks.page)
            .collect()
        )
        return {"uuid": file_uuid, "chunks": rows, "total": len(rows)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Video keyframes ───────────────────────────────────────────────────────────

@router.get("/frames/{file_uuid}")
def get_frames(file_uuid: str, limit: int = 12):
    try:
        frames_view = pxt.get_table(f"{config.APP_NAMESPACE}.video_frames")
        rows = list(
            frames_view.where(frames_view.uuid == UUID(file_uuid))
            .select(frame=frames_view.frame_thumbnail, pos=frames_view.pos)
            .limit(limit)
            .collect()
        )
        return {
            "uuid": file_uuid,
            "frames": [
                {"frame": r["frame"], "position": r["pos"]}
                for r in rows
            ],
            "total": len(rows),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Video transcription ──────────────────────────────────────────────────────

@router.get("/transcription/{file_uuid}")
def get_transcription(file_uuid: str):
    try:
        sentences_view = pxt.get_table(f"{config.APP_NAMESPACE}.video_sentences")
        rows = list(
            sentences_view.where(sentences_view.uuid == UUID(file_uuid))
            .select(text=sentences_view.text)
            .collect()
        )
        # Deduplicate while preserving order
        seen: set[str] = set()
        texts: list[str] = []
        for r in rows:
            t = r.get("text", "")
            if t and t not in seen:
                seen.add(t)
                texts.append(t)
        return {
            "uuid": file_uuid,
            "sentences": texts,
            "full_text": " ".join(texts),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
