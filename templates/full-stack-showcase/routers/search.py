"""Multimodal search across video segments, frames, and transcripts.

Gemini multimodal embeddings project text, images, audio, and video into the same
semantic space, enabling true cross-modal search:
- Text query  -> returns video segments, frames, AND transcripts
- Image query -> returns frames AND video segments
- Video query -> returns video segments AND frames
- Audio query -> returns video segments

Related events: given any search result, find semantically similar events across
the entire archive using a single Pixeltable .similarity() call.
"""

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

import config
import pixeltable as pxt
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from models import SearchResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/search", tags=["search"])

UPLOAD_DIR = Path(config.UPLOAD_FOLDER)


class TextSearchRequest(BaseModel):
    query: str
    types: list[str] = ["video_segment", "frame", "transcript"]
    limit: int = 20
    threshold: float = 0.15


class RelatedRequest(BaseModel):
    type: str
    text: str | None = None
    video_url: str | None = None
    uuid: str | None = None
    limit: int = 8


def _video_metadata(uuid_val: str) -> dict:
    """Look up video-level metadata (site, camera, location, asset, timestamp) for a given uuid."""
    try:
        vids = pxt.get_table(f"{config.NAMESPACE}.videos")
        rows = list(
            vids.where(vids.uuid == uuid_val)
            .select(
                site_name=vids.site_name,
                camera_id=vids.camera_id,
                location=vids.location,
                asset_id=vids.asset_id,
                recorded_at=vids.recorded_at,
            )
            .limit(1)
            .collect()
        )
        if rows:
            r = rows[0]
            return {k: r.get(k) for k in ("site_name", "camera_id", "location", "asset_id", "recorded_at") if r.get(k)}
    except Exception:
        pass
    return {}


def _search_segments(*, limit: int, threshold: float, **sim_kwargs: str) -> list[dict]:
    """Search video_segments with any modality kwarg (string=, image=, video=, audio=)."""
    results: list[dict] = []
    try:
        segs = pxt.get_table(f"{config.NAMESPACE}.video_segments")
        sim = segs.video_segment.similarity(**sim_kwargs)
        rows = list(
            segs.where(sim > threshold)
            .order_by(sim, asc=False)
            .select(
                uuid=segs.uuid,
                sim=sim,
                segment_start=segs.segment_start,
                segment_end=segs.segment_end,
                video_segment=segs.video_segment,
                source=segs.video,
                site_name=segs.site_name,
                camera_id=segs.camera_id,
            )
            .limit(limit)
            .collect()
        )
        for r in rows:
            video_path = str(r.get("video_segment", ""))
            seg_start = r.get("segment_start", 0)
            seg_end = r.get("segment_end", 0)
            results.append(
                {
                    "type": "video_segment",
                    "uuid": str(r.get("uuid", "")),
                    "similarity": round(r.get("sim", 0), 3),
                    "text": f"Segment {seg_start:.1f}s - {seg_end:.1f}s",
                    "video_url": f"/api/browse/media?path={video_path}" if video_path else None,
                    "metadata": {
                        "segment_start": seg_start,
                        "segment_end": seg_end,
                        "duration": round(seg_end - seg_start, 1) if seg_end and seg_start else None,
                        "source": os.path.basename(str(r.get("source", ""))),
                        "site_name": r.get("site_name"),
                        "camera_id": r.get("camera_id"),
                    },
                }
            )
    except Exception as e:
        logger.warning(f"Video segment search failed: {e}")
    return results


def _search_frames(*, limit: int, threshold: float, **sim_kwargs: str) -> list[dict]:
    """Search video_frames with any modality kwarg (string=, image=)."""
    results: list[dict] = []
    try:
        frames = pxt.get_table(f"{config.NAMESPACE}.video_frames")
        sim = frames.frame.similarity(**sim_kwargs)
        rows = list(
            frames.where(sim > threshold)
            .order_by(sim, asc=False)
            .select(
                uuid=frames.uuid,
                sim=sim,
                thumbnail=frames.frame_thumbnail,
                source=frames.video,
                site_name=frames.site_name,
                camera_id=frames.camera_id,
            )
            .limit(limit)
            .collect()
        )
        for r in rows:
            results.append(
                {
                    "type": "frame",
                    "uuid": str(r.get("uuid", "")),
                    "similarity": round(r.get("sim", 0), 3),
                    "thumbnail": r.get("thumbnail"),
                    "metadata": {
                        "source": os.path.basename(str(r.get("source", ""))),
                        "site_name": r.get("site_name"),
                        "camera_id": r.get("camera_id"),
                    },
                }
            )
    except Exception as e:
        logger.warning(f"Frame search failed: {e}")
    return results


def _search_transcripts(*, query: str, limit: int, threshold: float) -> list[dict]:
    """Search video_sentences via Gemini text embeddings."""
    results: list[dict] = []
    try:
        sents = pxt.get_table(f"{config.NAMESPACE}.video_sentences")
        sim = sents.text.similarity(string=query)
        rows = list(
            sents.where(sim > max(threshold, 0.3))
            .order_by(sim, asc=False)
            .select(
                text=sents.text,
                uuid=sents.uuid,
                sim=sim,
                site_name=sents.site_name,
                camera_id=sents.camera_id,
            )
            .limit(limit * 3)
            .collect()
        )
        seen_texts: set[str] = set()
        for r in rows:
            text = r.get("text", "")
            if text in seen_texts:
                continue
            seen_texts.add(text)
            results.append(
                {
                    "type": "transcript",
                    "uuid": str(r.get("uuid", "")),
                    "similarity": round(r.get("sim", 0), 3),
                    "text": text,
                    "metadata": {
                        "site_name": r.get("site_name"),
                        "camera_id": r.get("camera_id"),
                    },
                }
            )
    except Exception as e:
        logger.warning(f"Transcript search failed: {e}")
    return results


@router.post("", response_model=SearchResponse)
def search_text(body: TextSearchRequest):
    """Text search across ALL modalities: video segments, frames, and transcripts.

    Cross-modal similarity scores differ by modality (text-to-text > text-to-image
    > text-to-video), so we allocate a per-type quota then round-robin merge to
    ensure every requested type is represented in the final results.
    """
    per_type: dict[str, list[dict]] = {}
    n_types = len(body.types)
    per_limit = max(body.limit // max(n_types, 1), 5)

    if "video_segment" in body.types:
        per_type["video_segment"] = _search_segments(
            string=body.query,
            limit=per_limit,
            threshold=body.threshold,
        )

    if "frame" in body.types:
        per_type["frame"] = _search_frames(
            string=body.query,
            limit=per_limit,
            threshold=body.threshold,
        )

    if "transcript" in body.types:
        per_type["transcript"] = _search_transcripts(
            query=body.query,
            limit=per_limit,
            threshold=body.threshold,
        )

    merged: list[dict] = []
    iters = [iter(v) for v in per_type.values()]
    while iters and len(merged) < body.limit:
        next_iters = []
        for it in iters:
            item = next(it, None)
            if item is not None:
                merged.append(item)
                next_iters.append(it)
        iters = next_iters

    return {"query": body.query, "results": merged[: body.limit]}


def _save_upload(file: UploadFile) -> Path:
    ts = int(datetime.now().timestamp() * 1000)
    file_path = UPLOAD_DIR / f"query_{ts}_{file.filename}"
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return file_path


@router.post("/by-image", response_model=SearchResponse)
def search_by_image(file: UploadFile = File(...), limit: int = Form(20)):
    """Image search -> returns matching frames AND video segments (cross-modal)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_path = _save_upload(file)
    results: list[dict] = []

    results.extend(
        _search_frames(
            image=str(file_path),
            limit=limit,
            threshold=0.15,
        )
    )
    results.extend(
        _search_segments(
            image=str(file_path),
            limit=limit,
            threshold=0.15,
        )
    )

    file_path.unlink(missing_ok=True)
    results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
    return {"query": f"[image: {file.filename}]", "results": results[:limit]}


@router.post("/by-video", response_model=SearchResponse)
def search_by_video(file: UploadFile = File(...), limit: int = Form(20)):
    """Video clip search -> returns matching video segments AND frames (cross-modal)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_path = _save_upload(file)
    results: list[dict] = []

    results.extend(
        _search_segments(
            video=str(file_path),
            limit=limit,
            threshold=0.15,
        )
    )
    results.extend(
        _search_frames(
            image=str(file_path),
            limit=limit // 2,
            threshold=0.15,
        )
    )

    file_path.unlink(missing_ok=True)
    results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
    return {"query": f"[video: {file.filename}]", "results": results[:limit]}


@router.post("/by-audio", response_model=SearchResponse)
def search_by_audio(file: UploadFile = File(...), limit: int = Form(20)):
    """Audio search -> returns matching video segments (cross-modal audio-to-video)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_path = _save_upload(file)
    results: list[dict] = []

    results.extend(
        _search_segments(
            audio=str(file_path),
            limit=limit,
            threshold=0.15,
        )
    )

    file_path.unlink(missing_ok=True)
    results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
    return {"query": f"[audio: {file.filename}]", "results": results[:limit]}


@router.post("/related", response_model=SearchResponse)
def get_related_events(body: RelatedRequest):
    """Find events related to a given search result.

    Uses Pixeltable's embedding similarity to discover related events across
    the entire archive — text descriptions, video segments, and transcripts.
    A single .similarity() call per modality.
    """
    all_results: list[dict] = []
    per_limit = max(body.limit, 4)

    if body.text:
        all_results.extend(_search_frames(string=body.text, limit=per_limit, threshold=0.15))
        all_results.extend(_search_segments(string=body.text, limit=per_limit, threshold=0.15))
        all_results.extend(_search_transcripts(query=body.text, limit=per_limit, threshold=0.15))

    if body.type == "video_segment" and body.video_url:
        video_path = body.video_url.replace("/api/browse/media?path=", "")
        if os.path.exists(video_path):
            all_results.extend(_search_segments(video=video_path, limit=per_limit, threshold=0.15))

    seen: set[tuple[str, str, str]] = set()
    unique: list[dict] = []
    for r in all_results:
        key = (r["type"], r.get("uuid", ""), r.get("text", "") or "")
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)

    unique.sort(key=lambda x: x.get("similarity", 0), reverse=True)
    label = body.text[:60] if body.text else body.type
    return {"query": f"[related: {label}]", "results": unique[: body.limit]}
