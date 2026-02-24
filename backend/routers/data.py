"""Data pipeline endpoints: upload, list, detail, frames, transcription, detection."""
import logging
import os
import shutil
import uuid as uuid_lib
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
import pixeltable as pxt

import config
from models import MEDIA_ROW_MODELS

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

@router.post("/upload")
def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename")

    ext = Path(file.filename).suffix.lower().lstrip(".")
    if ext not in config.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: .{ext}")

    file_uuid = str(uuid_lib.uuid4())[:8]
    safe_name = f"{file_uuid}_{file.filename}"
    file_path = UPLOAD_DIR / safe_name

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    media_type = _classify_file(file.filename)
    table_path = TABLE_PATHS[media_type]
    table = pxt.get_table(table_path)

    row_model = MEDIA_ROW_MODELS[media_type]
    col_name = media_type if media_type != "document" else "document"
    row = row_model(**{
        col_name: str(file_path),
        "uuid": file_uuid,
        "timestamp": datetime.now(),
        "user_id": config.DEFAULT_USER_ID,
    })
    table.insert([row])

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
            d["name"] = os.path.basename(str(d.get("name", "")))
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
        where=(table.uuid == file_uuid) & (table.user_id == config.DEFAULT_USER_ID)
    )
    return {"message": "Deleted", "num_deleted": status.num_rows}


# ── Document chunks ───────────────────────────────────────────────────────────

@router.get("/chunks/{file_uuid}")
def get_chunks(file_uuid: str):
    try:
        chunks = pxt.get_table(f"{config.APP_NAMESPACE}.chunks")
        rows = list(
            chunks.where(chunks.uuid == file_uuid)
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
            frames_view.where(frames_view.uuid == file_uuid)
            .select(frame=frames_view.frame_thumbnail, pos=frames_view.pos)
            .limit(limit)
            .collect()
        )
        return {
            "uuid": file_uuid,
            "frames": [{"frame": r["frame"], "position": r["pos"]} for r in rows],
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
            sentences_view.where(sentences_view.uuid == file_uuid)
            .select(text=sentences_view.text)
            .collect()
        )
        texts = [r["text"] for r in rows if r.get("text")]
        return {
            "uuid": file_uuid,
            "sentences": texts,
            "full_text": " ".join(texts),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── On-demand detection (DETR) ────────────────────────────────────────────────

_model_cache: dict = {}


class DetectRequest(BaseModel):
    uuid: str
    source: str = "image"
    frame_idx: int | None = None
    threshold: float = 0.7


@router.post("/detect")
def detect_objects(body: DetectRequest):
    try:
        from transformers import DetrImageProcessor, DetrForObjectDetection
        from PIL import Image
        import torch

        model_key = "detr-resnet-50"
        if model_key not in _model_cache:
            processor = DetrImageProcessor.from_pretrained(
                "facebook/detr-resnet-50", revision="no_timm"
            )
            model = DetrForObjectDetection.from_pretrained(
                "facebook/detr-resnet-50", revision="no_timm"
            )
            _model_cache[model_key] = (processor, model)

        processor, model = _model_cache[model_key]

        if body.source == "image":
            table = pxt.get_table(TABLE_PATHS["image"])
            rows = list(
                table.where(table.uuid == body.uuid)
                .select(table.image)
                .collect()
            )
            if not rows:
                raise HTTPException(status_code=404, detail="Image not found")
            img = rows[0]["image"]
        else:
            frames_view = pxt.get_table(f"{config.APP_NAMESPACE}.video_frames")
            rows = list(
                frames_view.where(frames_view.uuid == body.uuid)
                .select(frames_view.frame)
                .collect()
            )
            if not rows:
                raise HTTPException(status_code=404, detail="No frames found")
            idx = body.frame_idx or 0
            if idx >= len(rows):
                idx = len(rows) - 1
            img = rows[idx]["frame"]

        if not isinstance(img, Image.Image):
            img = Image.open(str(img)).convert("RGB")

        inputs = processor(images=img, return_tensors="pt")
        with torch.no_grad():
            outputs = model(**inputs)

        target_sizes = torch.tensor([img.size[::-1]])
        results = processor.post_process_object_detection(
            outputs, target_sizes=target_sizes, threshold=body.threshold
        )[0]

        detections = []
        for score, label, box in zip(
            results["scores"], results["labels"], results["boxes"]
        ):
            x1, y1, x2, y2 = box.tolist()
            detections.append({
                "label": model.config.id2label[label.item()],
                "score": round(score.item(), 3),
                "box": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
            })

        return {
            "type": "detection",
            "model": model_key,
            "image_width": img.width,
            "image_height": img.height,
            "count": len(detections),
            "detections": detections,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Detection error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
