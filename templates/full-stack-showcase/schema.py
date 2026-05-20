"""Full-stack video intelligence platform — Pixeltable showcase.

Demonstrates every core Pixeltable primitive in one schema:
  - Multimodal tables (video, image, audio, text)
  - Computed columns (Gemini LLM, DETR CV, Whisper STT)
  - Views with iterators (frame_iterator, video_splitter, audio_splitter, string_splitter)
  - Multimodal embedding indexes (Gemini embed_content for cross-modal search)
  - Scene detection, panoptic segmentation, severity classification

    python schema.py        # create tables, views, indexes
    pxt serve sitewatch     # start the API
"""

import os

import config
import numpy as np
import pixeltable as pxt
from pixeltable.functions import image as pxt_image
from pixeltable.functions.audio import audio_splitter
from pixeltable.functions.huggingface import detr_for_segmentation
from pixeltable.functions.string import string_splitter
from pixeltable.functions.uuid import uuid7
from pixeltable.functions.video import (
    extract_audio,
    frame_iterator,
    get_duration,
    get_metadata,
    video_splitter,
)
from pixeltable.functions.vision import overlay_segmentation
from pixeltable.functions.whisper import transcribe as whisper_transcribe

HAVE_GEMINI = bool(os.environ.get("GEMINI_API_KEY"))
if HAVE_GEMINI:
    from pixeltable.functions.gemini import embed_content, generate_content

pxt.create_dir(config.NAMESPACE, if_exists="ignore")

# ── Videos table ──────────────────────────────────────────────────────────────

videos = pxt.create_table(
    f"{config.NAMESPACE}.videos",
    {
        "video": pxt.Video,
        "site_name": pxt.String,
        "camera_id": pxt.String,
        "location": pxt.String,
        "asset_id": pxt.String,
        "gps_lat": pxt.Float,
        "gps_lon": pxt.Float,
        "recorded_at": pxt.Timestamp,
        "tags": pxt.Json,
        "uuid": uuid7(),
        "timestamp": pxt.Timestamp,
    },
    primary_key=["uuid"],
    if_exists="ignore",
)

videos.add_computed_column(duration=get_duration(videos.video), if_exists="ignore")
videos.add_computed_column(metadata=get_metadata(videos.video), if_exists="ignore")

if HAVE_GEMINI:
    videos.add_computed_column(
        video_summary=generate_content(
            [videos.video, config.VIDEO_SUMMARY_PROMPT],
            model=config.GEMINI_MODEL,
        ),
        if_exists="ignore",
    )

# ── Frame extraction + DETR segmentation ──────────────────────────────────────

video_frames = pxt.create_view(
    f"{config.NAMESPACE}.video_frames",
    videos,
    iterator=frame_iterator(video=videos.video, fps=config.FRAME_FPS),
    if_exists="ignore",
)

video_frames.add_computed_column(
    frame_thumbnail=pxt_image.b64_encode(pxt_image.thumbnail(video_frames.frame, size=(320, 320))),
    if_exists="ignore",
)

video_frames.add_computed_column(
    detr_seg=detr_for_segmentation(
        video_frames.frame,
        model_id=config.DETR_MODEL,
        threshold=0.5,
    ),
    if_exists="ignore",
)

video_frames.add_computed_column(
    segmentation_overlay_b64=pxt_image.b64_encode(
        pxt_image.thumbnail(
            overlay_segmentation(
                video_frames.frame,
                video_frames.detr_seg.segmentation.astype(pxt.Array[(None, None), np.int32]),
                alpha=0.5,
                draw_contours=True,
                contour_thickness=2,
            ),
            size=(480, 480),
        )
    ),
    if_exists="ignore",
)

if HAVE_GEMINI:
    gemini_embed = embed_content.using(model=config.GEMINI_EMBEDDING_MODEL)

    video_frames.add_embedding_index(
        "frame",
        idx_name="frames_gemini_idx",
        embedding=gemini_embed,
        if_exists="ignore",
    )

# ── Video segments + Gemini analysis ──────────────────────────────────────────

video_segments = pxt.create_view(
    f"{config.NAMESPACE}.video_segments",
    videos,
    iterator=video_splitter(
        video=videos.video,
        duration=config.SEGMENT_DURATION,
        overlap=config.SEGMENT_OVERLAP,
        min_segment_duration=config.MIN_SEGMENT_DURATION,
        mode="fast",
    ),
    if_exists="ignore",
)

if HAVE_GEMINI:
    video_segments.add_computed_column(
        segment_analysis=generate_content(
            [video_segments.video_segment, config.SEGMENT_ANALYSIS_PROMPT],
            model=config.GEMINI_MODEL,
        ),
        if_exists="ignore",
    )

    video_segments.add_embedding_index(
        "video_segment",
        idx_name="segments_gemini_idx",
        embedding=gemini_embed,
        if_exists="ignore",
    )

# ── Scene detection ───────────────────────────────────────────────────────────

videos.add_computed_column(
    scene_cuts=videos.video.scene_detect_content(),
    if_exists="ignore",
)

# ── Audio transcription pipeline ──────────────────────────────────────────────

videos.add_computed_column(
    audio=extract_audio(videos.video, format="mp3"),
    if_exists="ignore",
)

audio_chunks = pxt.create_view(
    f"{config.NAMESPACE}.audio_chunks",
    videos,
    iterator=audio_splitter(audio=videos.audio, duration=config.AUDIO_CHUNK_DURATION),
    if_exists="ignore",
)

audio_chunks.add_computed_column(
    transcription=whisper_transcribe(audio_chunks.audio_segment, model=config.WHISPER_MODEL),
    if_exists="ignore",
)

video_sentences = pxt.create_view(
    f"{config.NAMESPACE}.video_sentences",
    audio_chunks.where(audio_chunks.transcription != None),  # noqa: E711
    iterator=string_splitter(
        text=audio_chunks.transcription.text,
        separators="sentence",
    ),
    if_exists="ignore",
)

if HAVE_GEMINI:
    video_sentences.add_embedding_index(
        "text",
        idx_name="sentences_gemini_idx",
        string_embed=gemini_embed,
        if_exists="ignore",
    )

# ── Query functions (used by pxt serve routes) ────────────────────────────────


@pxt.query
def list_videos():
    """All videos with metadata."""
    v = pxt.get_table(f"{config.NAMESPACE}.videos")
    return v.select(
        v.uuid,
        v.site_name,
        v.camera_id,
        v.location,
        v.asset_id,
        v.gps_lat,
        v.gps_lon,
        v.duration,
        v.recorded_at,
        v.timestamp,
        v.tags,
    ).order_by(v.timestamp, asc=False)


if HAVE_GEMINI:

    @pxt.query
    def search_frames(query_text: str, limit: int = 20):
        """Cross-modal search over video frames via Gemini embeddings."""
        f = pxt.get_table(f"{config.NAMESPACE}.video_frames")
        sim = f.frame.similarity(string=query_text)
        return (
            f.where(sim > 0.15)
            .order_by(sim, asc=False)
            .select(f.uuid, f.frame_thumbnail, f.site_name, f.camera_id, sim=sim)
            .limit(limit)
        )

    @pxt.query
    def search_segments(query_text: str, limit: int = 20):
        """Cross-modal search over video segments."""
        s = pxt.get_table(f"{config.NAMESPACE}.video_segments")
        sim = s.video_segment.similarity(string=query_text)
        return (
            s.where(sim > 0.15)
            .order_by(sim, asc=False)
            .select(
                s.uuid,
                s.segment_start,
                s.segment_end,
                s.video_segment,
                s.site_name,
                s.camera_id,
                sim=sim,
            )
            .limit(limit)
        )

    @pxt.query
    def search_transcripts(query_text: str, limit: int = 20):
        """Semantic search over Whisper transcripts."""
        sents = pxt.get_table(f"{config.NAMESPACE}.video_sentences")
        sim = sents.text.similarity(string=query_text)
        return (
            sents.where(sim > 0.3)
            .order_by(sim, asc=False)
            .select(sents.text, sents.uuid, sents.site_name, sents.camera_id, sim=sim)
            .limit(limit)
        )


if __name__ == "__main__":
    print("Schema initialized. Run: uvicorn app:app --reload")
    if not HAVE_GEMINI:
        print("  Note: Set GEMINI_API_KEY to enable LLM analysis + cross-modal search.")
