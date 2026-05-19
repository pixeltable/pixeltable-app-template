"""Video Intelligence Pipeline — declarative video analysis with Pixeltable.

Ingest video → extract frames + audio → CLIP embeddings, Whisper transcription,
DETR object detection → multi-modal search (visual, spoken, objects).

    python schema.py        # create tables, views, indexes
    pxt serve videointel    # start the API (reads routes from pyproject.toml)
"""

import os

import pixeltable as pxt

import functions
from pixeltable.functions import image as pxt_image
from pixeltable.functions.audio import audio_splitter
from pixeltable.functions.huggingface import clip, detr_for_object_detection, sentence_transformer
from pixeltable.functions.string import string_splitter
from pixeltable.functions.uuid import uuid7
from pixeltable.functions.video import extract_audio, frame_iterator
from pixeltable.functions.whisper import transcribe as whisper_transcribe

pxt.create_dir('videointel', if_exists='ignore')

clip_embed = clip.using(model_id='openai/clip-vit-base-patch32')
text_embed = sentence_transformer.using(model_id='all-MiniLM-L6-v2')

# ── Videos table ─────────────────────────────────────────────────────────────

videos = pxt.create_table(
    'videointel.videos',
    {'video': pxt.Video, 'title': pxt.String, 'uuid': uuid7(), 'timestamp': pxt.Timestamp},
    primary_key=['uuid'],
    if_exists='ignore',
)

# ── Frame extraction ─────────────────────────────────────────────────────────

frames = pxt.create_view(
    'videointel.frames',
    videos,
    iterator=frame_iterator(video=videos.video, fps=1.0),
    if_exists='ignore',
)

frames.add_computed_column(
    thumbnail=pxt_image.b64_encode(pxt_image.thumbnail(frames.frame, size=(320, 320))),
    if_exists='ignore',
)

frames.add_embedding_index(
    column='frame', idx_name='frames_clip_idx', embedding=clip_embed, if_exists='ignore'
)

# ── Object detection (optional — requires timm) ─────────────────────────────

try:
    frames.add_computed_column(
        detections=detr_for_object_detection(
            frames.frame, model_id='facebook/detr-resnet-50', threshold=0.7
        ),
        if_exists='ignore',
    )
except Exception as exc:
    print(f'Skipping DETR object detection: {exc}')

# ── Audio extraction + transcription ─────────────────────────────────────────

videos.add_computed_column(
    audio=extract_audio(videos.video, format='mp3'), if_exists='ignore'
)

audio_chunks = pxt.create_view(
    'videointel.audio_chunks',
    videos,
    iterator=audio_splitter(audio=videos.audio, duration=30.0),
    if_exists='ignore',
)

audio_chunks.add_computed_column(
    transcription=whisper_transcribe(audio_chunks.audio_segment, model='base.en'),
    if_exists='ignore',
)

# ── Transcript sentences + text search ───────────────────────────────────────

transcript_sentences = pxt.create_view(
    'videointel.transcript_sentences',
    audio_chunks.where(audio_chunks.transcription != None),  # noqa: E711
    iterator=string_splitter(text=audio_chunks.transcription.text, separators='sentence'),
    if_exists='ignore',
)

transcript_sentences.add_embedding_index(
    column='text', idx_name='transcript_text_idx', string_embed=text_embed, if_exists='ignore'
)

# ── Scene descriptions (optional — requires OPENAI_API_KEY) ─────────────────

if os.getenv('OPENAI_API_KEY'):
    try:
        from pixeltable.functions.openai import chat_completions

        frames.add_computed_column(
            scene_description=chat_completions(
                messages=[{
                    'role': 'user',
                    'content': [
                        {'type': 'image_url', 'image_url': {'url': frames.frame}},
                        {'type': 'text', 'text': 'Describe this video frame in one sentence.'},
                    ],
                }],
                model='gpt-4o-mini',
            ).choices[0].message.content,
            if_exists='ignore',
        )
    except Exception as exc:
        print(f'Skipping LLM scene descriptions: {exc}')

# ── Query functions ──────────────────────────────────────────────────────────


@pxt.query
def search_visual(query_text: str, limit: int = 20):
    """CLIP similarity search on video frames."""
    sim = frames.frame.similarity(string=query_text)
    return (
        frames.where(sim > 0.2)
        .order_by(sim, asc=False)
        .select(
            frames.thumbnail,
            timestamp=frames.frame_attrs.time,
            source_video=frames.video,
            sim=sim,
        )
        .limit(limit)
    )


@pxt.query
def search_spoken(query_text: str, limit: int = 20):
    """Semantic search over transcribed speech."""
    sim = transcript_sentences.text.similarity(string=query_text)
    return (
        transcript_sentences.where(sim > 0.3)
        .order_by(sim, asc=False)
        .select(
            transcript_sentences.text,
            source_video=transcript_sentences.video,
            segment_start=transcript_sentences.segment_start,
            sim=sim,
        )
        .limit(limit)
    )


@pxt.query
def search_objects(label: str, limit: int = 50):
    """Filter frames containing a specific detected object label."""
    return (
        frames.where(functions.has_label(frames.detections.label_text, label))
        .select(
            frames.thumbnail,
            timestamp=frames.frame_attrs.time,
            source_video=frames.video,
            labels=frames.detections.label_text,
            scores=frames.detections.scores,
        )
        .limit(limit)
    )


@pxt.query
def search_all(query_text: str, limit: int = 10):
    """Visual similarity search across all video frames (primary modality)."""
    sim = frames.frame.similarity(string=query_text)
    return (
        frames.where(sim > 0.2)
        .order_by(sim, asc=False)
        .select(
            frames.thumbnail,
            timestamp=frames.frame_attrs.time,
            source_video=frames.video,
            sim=sim,
        )
        .limit(limit)
    )


if __name__ == '__main__':
    print('Video intelligence schema initialized.')
