"""Video Intelligence Pipeline — class-based declarative schema.

Equivalent to templates/video-search/schema.py rewritten using
pxt.Model / pxt.ViewModel / Column / create_all().

Original: 188 lines, 10x if_exists="ignore", scattered add_computed_column/add_embedding_index.
This version: ~120 lines, zero if_exists, co-located indexes and computed columns.
"""

import os

from pxt_declarative import Column, EmbeddingIndex, Model, ViewModel, create_all

# In a real schema, these would be actual Pixeltable imports:
# import pixeltable as pxt
# from pixeltable.functions import image as pxt_image
# from pixeltable.functions.audio import audio_splitter
# from pixeltable.functions.huggingface import clip, detr_for_object_detection, sentence_transformer
# from pixeltable.functions.string import string_splitter
# from pixeltable.functions.uuid import uuid7
# from pixeltable.functions.video import extract_audio, frame_iterator
# from pixeltable.functions.whisper import transcribe as whisper_transcribe

# For this prototype, we use placeholder sentinels
class _pxt:
    Video = "pxt.Video"
    String = "pxt.String"
    Timestamp = "pxt.Timestamp"


def uuid7():
    return "uuid7()"


def extract_audio(col, format="mp3"):
    return ("extract_audio", col, format)


def frame_iterator(video=None, fps=1.0):
    return ("frame_iterator", video, fps)


def audio_splitter(audio=None, duration=30.0):
    return ("audio_splitter", audio, duration)


def whisper_transcribe(audio, model="base.en"):
    return ("whisper_transcribe", audio, model)


def string_splitter(text=None, separators="sentence"):
    return ("string_splitter", text, separators)


def pxt_image_thumbnail(img, size=(320, 320)):
    return ("thumbnail", img, size)


def pxt_image_b64_encode(img):
    return ("b64_encode", img)


clip_embed = "clip.using(openai/clip-vit-base-patch32)"
text_embed = "sentence_transformer.using(all-MiniLM-L6-v2)"


# ═══════════════════════════════════════════════════════════════════════════════
# DECLARATIVE SCHEMA -- compare with templates/video-search/schema.py
# ═══════════════════════════════════════════════════════════════════════════════


class Videos(Model):
    __tablename__ = "videointel.videos"
    __primary_key__ = ["uuid"]

    video: _pxt.Video
    title: _pxt.String
    uuid: _pxt.String = uuid7()
    timestamp: _pxt.Timestamp

    audio = extract_audio(Column.video, format="mp3")


class Frames(ViewModel):
    __tablename__ = "videointel.frames"
    __base__ = frame_iterator(video=Videos.video, fps=1.0)

    thumbnail = pxt_image_b64_encode(
        pxt_image_thumbnail(Column.frame, size=(320, 320))
    )

    __indexes__ = [
        EmbeddingIndex(
            Column.frame, idx_name="frames_clip_idx", embedding=clip_embed
        )
    ]


class AudioChunks(ViewModel):
    __tablename__ = "videointel.audio_chunks"
    __base__ = audio_splitter(audio=Videos.audio, duration=30.0)

    transcription = whisper_transcribe(Column.audio_segment, model="base.en")


class TranscriptSentences(ViewModel):
    __tablename__ = "videointel.transcript_sentences"
    __parent__ = AudioChunks
    __filter__ = Column.transcription != None
    __iterator__ = string_splitter(
        text=AudioChunks.transcription.text, separators="sentence"
    )

    __indexes__ = [
        EmbeddingIndex(
            Column.text,
            idx_name="transcript_text_idx",
            string_embed=text_embed,
        )
    ]


# --- Conditional features (post-class mutation) ---

if os.getenv("OPENAI_API_KEY"):
    try:
        Frames.register_column(
            "scene_description",
            "chat_completions(...).choices[0].message.content",
        )
    except Exception:
        pass

try:
    Frames.register_column(
        "detections", "detr_for_object_detection(Column.frame, ...)"
    )
except Exception:
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION: dry_run to inspect execution plan
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from pxt_declarative import list_models

    print("=== Registered models ===")
    for name, cls in list_models("videointel").items():
        kind = "ViewModel" if cls._pxt_is_view else "Model"
        stored = list(cls._pxt_stored_columns.keys())
        computed = list(cls._pxt_computed_columns.keys())
        registered = list(cls._pxt_registered_columns.keys())
        indexes = [repr(idx) for idx in cls._pxt_indexes]
        print(f"\n{kind}: {name}")
        print(f"  Stored columns: {stored}")
        print(f"  Computed columns: {computed}")
        if registered:
            print(f"  Registered columns: {registered}")
        if indexes:
            print(f"  Indexes: {indexes}")
        if cls._pxt_primary_key:
            print(f"  Primary key: {cls._pxt_primary_key}")
        if cls._pxt_view_base:
            print(f"  View base: {cls._pxt_view_base!r}")
        if cls._pxt_view_parent:
            print(f"  View parent: {cls._pxt_view_parent}")
        if cls._pxt_view_filter:
            print(f"  View filter: {cls._pxt_view_filter!r}")
        if cls._pxt_view_iterator:
            print(f"  View iterator: {cls._pxt_view_iterator!r}")

    print("\n=== Execution plan (dry_run) ===")
    plan = create_all("videointel", dry_run=True)
    for i, name in enumerate(plan["order"], 1):
        print(f"  {i}. {name}")
