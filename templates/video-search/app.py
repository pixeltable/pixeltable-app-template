"""Video intelligence application file.

Ingest video, extract frames and audio, embed, transcribe, detect objects, search.

    pxt schema update app.py videointel
    pxt service update app.py videointel
    pxt service run app.py videointel
"""

# ruff: noqa: F821

from __future__ import annotations

import functions
import pixeltable as pxt
import pixeltable.functions as pxtf
from pixeltable.functions import image as pxt_image
from pixeltable.functions.huggingface import clip, detr_for_object_detection, sentence_transformer
from pixeltable.functions.whisper import transcribe as whisper_transcribe
from pixeltable.serving import FastAPIRouter

TableModel = pxt.model_base()

clip_embed = clip.using(model_id="openai/clip-vit-base-patch32")
text_embed = sentence_transformer.using(model_id="all-MiniLM-L6-v2")


class Videos(TableModel, name="videos"):
    video: pxt.Video
    title: pxt.String
    uuid = pxt.Column(value=pxtf.uuid.uuid7(), primary_key=True)
    timestamp: pxt.Timestamp | None
    audio = pxtf.video.extract_audio(video, format="mp3")


class Frames(TableModel, name="frames", base=Videos, iterator=pxtf.video.frame_iterator(Videos.video, fps=1.0)):
    thumbnail = pxt_image.b64_encode(pxt_image.thumbnail(frame, size=(320, 320)))
    detections = detr_for_object_detection(frame, model_id="facebook/detr-resnet-50", threshold=0.7)
    __indexes__ = [
        pxt.EmbeddingIndex(frame, embedding=clip_embed, name="frames_clip_idx"),
    ]


class AudioChunks(
    TableModel,
    name="audio_chunks",
    base=Videos,
    iterator=pxtf.audio.audio_splitter(Videos.audio, duration=30.0),
):
    transcription = whisper_transcribe(audio_segment, model="base.en")


class TranscriptSentences(
    TableModel,
    name="transcript_sentences",
    base=AudioChunks.where(AudioChunks.transcription != None),  # noqa: E711
    iterator=pxtf.string.string_splitter(AudioChunks.transcription.text, separators="sentence"),
):
    __indexes__ = [
        pxt.EmbeddingIndex(text, embedding=text_embed, name="transcript_text_idx"),
    ]


@pxt.query
def search_visual(query_text: str, limit: int = 20) -> pxt.Query:
    """CLIP similarity search on video frames."""
    sim = Frames.frame.similarity(string=query_text)
    return (
        Frames.where(sim > 0.2)
        .order_by(sim, asc=False)
        .select(
            Frames.thumbnail,
            timestamp=Frames.frame_attrs.time,
            source_video=Frames.video,
            score=sim,
        )
        .limit(limit)
    )


@pxt.query
def search_spoken(query_text: str, limit: int = 20) -> pxt.Query:
    """Semantic search over transcribed speech."""
    sim = TranscriptSentences.text.similarity(string=query_text)
    return (
        TranscriptSentences.where(sim > 0.3)
        .order_by(sim, asc=False)
        .select(
            TranscriptSentences.text,
            source_video=TranscriptSentences.video,
            segment_start=TranscriptSentences.segment_start,
            score=sim,
        )
        .limit(limit)
    )


@pxt.query
def search_objects(label: str, limit: int = 50) -> pxt.Query:
    """Filter frames containing a specific detected object label."""
    return (
        Frames.where(functions.has_label(Frames.detections.label_text, label))
        .select(
            Frames.thumbnail,
            timestamp=Frames.frame_attrs.time,
            source_video=Frames.video,
            labels=Frames.detections.label_text,
            scores=Frames.detections.scores,
        )
        .limit(limit)
    )


@pxt.query
def search_all(query_text: str, limit: int = 10) -> pxt.Query:
    """Visual similarity search across all video frames (primary modality)."""
    sim = Frames.frame.similarity(string=query_text)
    return (
        Frames.where(sim > 0.2)
        .order_by(sim, asc=False)
        .select(
            Frames.thumbnail,
            timestamp=Frames.frame_attrs.time,
            source_video=Frames.video,
            score=sim,
        )
        .limit(limit)
    )


api = FastAPIRouter(name="videointel", prefix="/api")
api.add_insert_route(
    Videos,
    path="/ingest",
    uploadfile_inputs=["video"],
    inputs=[Videos.title],
    outputs=[Videos.uuid],
    background=True,
)
api.add_query_route(path="/search/visual", query=search_visual, method="post")
api.add_query_route(path="/search/spoken", query=search_spoken, method="post")
api.add_query_route(path="/search", query=search_all, method="post")
api.add_query_route(path="/search/objects", query=search_objects, method="post")
