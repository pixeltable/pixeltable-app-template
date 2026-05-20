"""Multi-medium browse endpoints: frames (DETR), segments (Gemini AI), scenes, and audio."""

import itertools
import logging
import os
from pathlib import Path

import config
import pixeltable as pxt
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from functions import parse_segment_analysis, severity_from_analysis
from models import BrowseAudioItem, BrowseDetectionItem, BrowseFrameItem, BrowseSegmentItem

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/browse", tags=["browse"])


def _table(name: str):
    return pxt.get_table(f"{config.NAMESPACE}.{name}")


def _interleave_by_video(rows: list[dict]) -> list[dict]:
    """Round-robin interleave rows so consecutive items come from different videos."""
    by_video: dict[str, list[dict]] = {}
    for r in rows:
        by_video.setdefault(str(r.get("uuid", "")), []).append(r)
    return [r for r in itertools.chain.from_iterable(itertools.zip_longest(*by_video.values())) if r is not None]


# ---------------------------------------------------------------------------
# DETR detections (pre-computed on video_frames)
# ---------------------------------------------------------------------------


@router.get("/detections", response_model=list[BrowseDetectionItem])
def browse_detections(
    site_name: str | None = None,
    label: str | None = None,
    limit: int = 48,
    offset: int = 0,
):
    """Browse pre-computed DETR panoptic segmentation results from video frames."""
    try:
        frames = _table("video_frames")
        base = frames.where(frames.site_name == site_name) if site_name else frames
        rows = list(
            base.select(
                uuid=frames.uuid,
                segmentation_overlay_b64=frames.segmentation_overlay_b64,
                detr_seg=frames.detr_seg,
                site_name=frames.site_name,
                camera_id=frames.camera_id,
                asset_id=frames.asset_id,
            ).collect()
        )
        interleaved = _interleave_by_video(rows)

        items: list[dict] = []
        for r in interleaved[offset:]:
            seg = r.get("detr_seg") or {}
            segments_info = seg.get("segments_info", [])
            labels = sorted({s["label_text"] for s in segments_info if s.get("label_text")})

            if label and label not in labels:
                continue

            items.append(
                {
                    "uuid": str(r.get("uuid", "")),
                    "segmentation_overlay": r.get("segmentation_overlay_b64", ""),
                    "detected_labels": labels,
                    "segments_info": segments_info,
                    "site_name": r.get("site_name"),
                    "camera_id": r.get("camera_id"),
                    "asset_id": r.get("asset_id"),
                }
            )
            if len(items) >= limit:
                break
        return items
    except Exception as e:
        logger.warning(f"Browse detections failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Frames (thumbnails only — AI analysis is on segments)
# ---------------------------------------------------------------------------


@router.get("/frames", response_model=list[BrowseFrameItem])
def browse_frames(
    site_name: str | None = None,
    limit: int = 60,
    offset: int = 0,
):
    """Paginated frame thumbnail browser."""
    try:
        frames = _table("video_frames")
        base = frames.where(frames.site_name == site_name) if site_name else frames
        rows = list(
            base.select(
                uuid=frames.uuid,
                frame=frames.frame_thumbnail,
                site_name=frames.site_name,
                camera_id=frames.camera_id,
                asset_id=frames.asset_id,
            ).collect()
        )
        interleaved = _interleave_by_video(rows)
        items: list[dict] = []
        for r in interleaved[offset:]:
            items.append(
                {
                    "uuid": str(r.get("uuid", "")),
                    "frame": r.get("frame", ""),
                    "site_name": r.get("site_name"),
                    "camera_id": r.get("camera_id"),
                    "asset_id": r.get("asset_id"),
                }
            )
            if len(items) >= limit:
                break
        return items
    except Exception as e:
        logger.warning(f"Browse frames failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Segments (Gemini AI analysis — description, severity, PPE)
# ---------------------------------------------------------------------------


@router.get("/segments", response_model=list[BrowseSegmentItem])
def browse_segments(
    site_name: str | None = None,
    severity: str | None = None,
    alerts_only: bool = False,
    limit: int = 48,
    offset: int = 0,
):
    """Paginated video segment browser with Gemini AI analysis."""
    try:
        segs = _table("video_segments")
        base = segs.where(segs.site_name == site_name) if site_name else segs
        rows = list(
            base.select(
                uuid=segs.uuid,
                segment_start=segs.segment_start,
                segment_end=segs.segment_end,
                video_segment=segs.video_segment,
                segment_analysis=segs.segment_analysis,
                site_name=segs.site_name,
                camera_id=segs.camera_id,
                asset_id=segs.asset_id,
            ).collect()
        )
        interleaved = _interleave_by_video(rows)
        items: list[dict] = []
        for r in interleaved[offset:]:
            analysis = parse_segment_analysis(r.get("segment_analysis"))
            sev = severity_from_analysis(analysis)
            if alerts_only and sev == "info":
                continue
            if severity and sev != severity:
                continue
            video_path = str(r.get("video_segment", ""))
            items.append(
                {
                    "uuid": str(r.get("uuid", "")),
                    "segment_start": r.get("segment_start", 0),
                    "segment_end": r.get("segment_end", 0),
                    "video_url": f"/api/browse/media?path={video_path}" if video_path else None,
                    "description": analysis.get("description", ""),
                    "severity": sev,
                    "severity_reason": analysis.get("severity_reason", ""),
                    "ppe_status": analysis.get("ppe_status", "N_A"),
                    "ppe_details": analysis.get("ppe_details", ""),
                    "equipment": analysis.get("equipment", []),
                    "hazards": analysis.get("hazards", []),
                    "site_name": r.get("site_name"),
                    "camera_id": r.get("camera_id"),
                    "asset_id": r.get("asset_id"),
                }
            )
            if len(items) >= limit:
                break
        return items
    except Exception as e:
        logger.warning(f"Browse segments failed: {e}")
        return []


@router.get("/media")
def serve_media(path: str):
    """Serve a Pixeltable-managed media file (video segment, audio chunk)."""
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    media_types = {".mp3": "audio/mpeg", ".wav": "audio/wav"}
    return FileResponse(file_path, media_type=media_types.get(file_path.suffix, "video/mp4"))


@router.get("/scenes", response_model=list[dict])
def browse_scenes(site_name: str | None = None, limit: int = 48, offset: int = 0):
    """Browse scenes extracted from all videos, with playable video URLs."""
    try:
        videos = _table("videos")
        base = videos.where(videos.site_name == site_name) if site_name else videos
        rows = list(
            base.select(
                uuid=videos.uuid,
                scene_cuts=videos.scene_cuts,
                source=videos.video,
                site_name=videos.site_name,
                camera_id=videos.camera_id,
            ).collect()
        )
        items: list[dict] = []
        for r in rows:
            video_path = str(r.get("source", ""))
            for sc in r.get("scene_cuts") or []:
                start = sc.get("start_time", 0)
                duration = sc.get("duration", 0)
                items.append(
                    {
                        "uuid": str(r.get("uuid", "")),
                        "scene_start": start,
                        "scene_end": start + duration,
                        "source": os.path.basename(video_path),
                        "video_url": f"/api/browse/media?path={video_path}#t={start:.1f},{start + duration:.1f}"
                        if video_path
                        else None,
                        "site_name": r.get("site_name"),
                        "camera_id": r.get("camera_id"),
                    }
                )
        return items[offset : offset + limit]
    except Exception as e:
        logger.warning(f"Browse scenes failed: {e}")
        return []


@router.get("/audio", response_model=list[BrowseAudioItem])
def browse_audio(site_name: str | None = None, limit: int = 48, offset: int = 0):
    """Browse audio chunks with transcription text and playable audio."""
    try:
        chunks = _table("audio_chunks")
        base = chunks.where(chunks.site_name == site_name) if site_name else chunks
        rows = list(
            base.select(
                uuid=chunks.uuid,
                audio_segment=chunks.audio_segment,
                transcription=chunks.transcription,
                site_name=chunks.site_name,
                camera_id=chunks.camera_id,
            )
            .limit(limit + offset)
            .collect()
        )
        items: list[dict] = []
        for r in rows[offset:]:
            raw = r.get("transcription")
            text = raw.get("text", "") if isinstance(raw, dict) else ""
            audio_path = str(r.get("audio_segment", ""))
            items.append(
                {
                    "uuid": str(r.get("uuid", "")),
                    "audio_url": f"/api/browse/media?path={audio_path}" if audio_path else None,
                    "transcription": text.strip() if text else None,
                    "site_name": r.get("site_name"),
                    "camera_id": r.get("camera_id"),
                }
            )
        return items[:limit]
    except Exception as e:
        logger.warning(f"Browse audio failed: {e}")
        return []
