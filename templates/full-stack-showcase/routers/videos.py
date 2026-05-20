"""Video management endpoints: upload, list, delete, frames, segments, scenes, transcription."""

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from uuid import UUID

import config
import pixeltable as pxt
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from functions import gemini_text, parse_segment_analysis, severity_from_analysis
from models import (
    AlertsResponse,
    DeleteResponse,
    FramesResponse,
    ScenesResponse,
    SegmentsResponse,
    TranscriptionResponse,
    UploadResponse,
    VideoDetail,
    VideoItem,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/videos", tags=["videos"])

UPLOAD_DIR = Path(config.UPLOAD_FOLDER)
UPLOAD_DIR.mkdir(exist_ok=True)

TABLE = f"{config.NAMESPACE}.videos"


# -- Upload -----------------------------------------------------------------


@router.post("/upload", status_code=201, response_model=UploadResponse)
def upload_video(
    file: UploadFile = File(...),
    site_name: str = Form("Default Site"),
    camera_id: str = Form("CAM-01"),
    location: str = Form(""),
    asset_id: str = Form("XFMR-SUB-B-014"),
    gps_lat: float = Form(37.7749),
    gps_lon: float = Form(-122.4194),
    tags: str = Form(""),
):
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

    table = pxt.get_table(TABLE)
    current_ts = datetime.now()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    table.insert(
        [
            {
                "video": str(file_path),
                "site_name": site_name,
                "camera_id": camera_id,
                "location": location,
                "asset_id": asset_id,
                "gps_lat": gps_lat,
                "gps_lon": gps_lon,
                "recorded_at": current_ts,
                "tags": tag_list,
                "timestamp": current_ts,
            }
        ]
    )

    rows = list(table.where(table.timestamp == current_ts).select(table.uuid).limit(1).collect())
    file_uuid = str(rows[0]["uuid"]) if rows else "unknown"

    return {"message": "Video uploaded", "filename": file.filename, "uuid": file_uuid}


# -- List videos ------------------------------------------------------------


@router.get("", response_model=list[VideoItem])
def list_videos(site_name: str | None = None):
    try:
        table = pxt.get_table(TABLE)
        base = table.where(table.site_name == site_name) if site_name else table
        query = base.select(
            uuid=table.uuid,
            name=table.video,
            site_name=table.site_name,
            camera_id=table.camera_id,
            location=table.location,
            asset_id=table.asset_id,
            gps_lat=table.gps_lat,
            gps_lon=table.gps_lon,
            duration=table.duration,
            recorded_at=table.recorded_at,
            timestamp=table.timestamp,
            tags=table.tags,
        ).order_by(table.timestamp, asc=False)

        rows = list(query.collect())
        results: list[dict] = []
        for r in rows:
            results.append(
                {
                    "uuid": str(r.get("uuid", "")),
                    "name": os.path.basename(str(r.get("name", ""))),
                    "site_name": r.get("site_name", ""),
                    "camera_id": r.get("camera_id", ""),
                    "location": r.get("location", ""),
                    "asset_id": r.get("asset_id"),
                    "gps_lat": r.get("gps_lat"),
                    "gps_lon": r.get("gps_lon"),
                    "duration": r.get("duration"),
                    "recorded_at": r["recorded_at"].isoformat() if isinstance(r.get("recorded_at"), datetime) else None,
                    "timestamp": r["timestamp"].isoformat() if isinstance(r.get("timestamp"), datetime) else None,
                    "tags": r.get("tags", []),
                }
            )
        return results
    except Exception as e:
        logger.warning(f"Could not list videos: {e}")
        return []


# -- Get video detail -------------------------------------------------------


@router.get("/{video_uuid}", response_model=VideoDetail)
def get_video(video_uuid: str):
    try:
        table = pxt.get_table(TABLE)
        rows = list(
            table.where(table.uuid == UUID(video_uuid))
            .select(
                uuid=table.uuid,
                name=table.video,
                site_name=table.site_name,
                camera_id=table.camera_id,
                location=table.location,
                asset_id=table.asset_id,
                gps_lat=table.gps_lat,
                gps_lon=table.gps_lon,
                duration=table.duration,
                recorded_at=table.recorded_at,
                tags=table.tags,
                video_summary=table.video_summary,
                metadata=table.metadata,
            )
            .limit(1)
            .collect()
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Video not found")
        r = rows[0]
        summary_text = gemini_text(r.get("video_summary")) or None
        return {
            "uuid": str(r.get("uuid", "")),
            "name": os.path.basename(str(r.get("name", ""))),
            "site_name": r.get("site_name", ""),
            "camera_id": r.get("camera_id", ""),
            "location": r.get("location", ""),
            "asset_id": r.get("asset_id"),
            "gps_lat": r.get("gps_lat"),
            "gps_lon": r.get("gps_lon"),
            "duration": r.get("duration"),
            "recorded_at": r["recorded_at"].isoformat() if isinstance(r.get("recorded_at"), datetime) else None,
            "tags": r.get("tags", []),
            "video_summary": summary_text,
            "metadata": r.get("metadata"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -- Delete video -----------------------------------------------------------


@router.delete("/{video_uuid}", response_model=DeleteResponse)
def delete_video(video_uuid: str):
    table = pxt.get_table(TABLE)
    status = table.delete(where=(table.uuid == UUID(video_uuid)))
    return {"message": "Deleted", "num_deleted": status.num_rows}


# -- Frames -----------------------------------------------------------------


@router.get("/{video_uuid}/frames", response_model=FramesResponse)
def get_frames(video_uuid: str, limit: int = 24):
    try:
        frames_view = pxt.get_table(f"{config.NAMESPACE}.video_frames")
        rows = list(
            frames_view.where(frames_view.uuid == UUID(video_uuid))
            .select(frame=frames_view.frame_thumbnail)
            .limit(limit)
            .collect()
        )
        items: list[dict] = []
        for r in rows:
            items.append({"frame": r.get("frame", "")})
        return FramesResponse(uuid=video_uuid, frames=items, total=len(items))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -- Segments ---------------------------------------------------------------


@router.get("/{video_uuid}/segments", response_model=SegmentsResponse)
def get_segments(video_uuid: str, limit: int = 50):
    try:
        seg_view = pxt.get_table(f"{config.NAMESPACE}.video_segments")
        rows = list(
            seg_view.where(seg_view.uuid == UUID(video_uuid))
            .select(
                segment_start=seg_view.segment_start,
                segment_end=seg_view.segment_end,
                uuid=seg_view.uuid,
            )
            .limit(limit)
            .collect()
        )
        items = [
            {"segment_start": r["segment_start"], "segment_end": r["segment_end"], "uuid": str(r["uuid"])} for r in rows
        ]
        return SegmentsResponse(uuid=video_uuid, segments=items, total=len(items))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -- Scenes -----------------------------------------------------------------


@router.get("/{video_uuid}/scenes", response_model=ScenesResponse)
def get_scenes(video_uuid: str):
    try:
        table = pxt.get_table(TABLE)
        rows = list(table.where(table.uuid == UUID(video_uuid)).select(scene_cuts=table.scene_cuts).limit(1).collect())
        if not rows or not rows[0].get("scene_cuts"):
            return ScenesResponse(uuid=video_uuid, scenes=[], total=0)
        items = [
            {
                "scene_start": sc.get("start_time", 0),
                "scene_end": sc.get("start_time", 0) + sc.get("duration", 0),
            }
            for sc in rows[0]["scene_cuts"]
        ]
        return ScenesResponse(uuid=video_uuid, scenes=items, total=len(items))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -- Transcription ----------------------------------------------------------


@router.get("/{video_uuid}/transcription", response_model=TranscriptionResponse)
def get_transcription(video_uuid: str):
    try:
        sentences_view = pxt.get_table(f"{config.NAMESPACE}.video_sentences")
        rows = list(
            sentences_view.where(sentences_view.uuid == UUID(video_uuid)).select(text=sentences_view.text).collect()
        )
        seen: set[str] = set()
        texts: list[str] = []
        for r in rows:
            t = r.get("text", "")
            if t and t not in seen:
                seen.add(t)
                texts.append(t)
        return {"uuid": video_uuid, "sentences": texts, "full_text": " ".join(texts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -- Alerts for a video -----------------------------------------------------


@router.get("/{video_uuid}/alerts", response_model=AlertsResponse)
def get_video_alerts(video_uuid: str, limit: int = 50):
    try:
        segs = pxt.get_table(f"{config.NAMESPACE}.video_segments")
        rows = list(
            segs.where(segs.uuid == UUID(video_uuid))
            .select(
                uuid=segs.uuid,
                segment_analysis=segs.segment_analysis,
                site_name=segs.site_name,
                camera_id=segs.camera_id,
            )
            .limit(limit * 3)
            .collect()
        )
        items = []
        for r in rows:
            analysis = parse_segment_analysis(r.get("segment_analysis"))
            sev = severity_from_analysis(analysis)
            if sev == "info":
                continue
            items.append(
                {
                    "uuid": str(r.get("uuid", "")),
                    "frame": "",
                    "segment_labels": analysis.get("equipment", []),
                    "severity": sev,
                    "frame_description": analysis.get("description", ""),
                    "severity_reason": analysis.get("severity_reason", ""),
                }
            )
            if len(items) >= limit:
                break
        return AlertsResponse(alerts=items, total=len(items))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
