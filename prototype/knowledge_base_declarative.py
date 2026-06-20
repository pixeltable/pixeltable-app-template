"""Knowledge Base -- class-based declarative schema.

Equivalent to templates/knowledge-base/schema.py.
Original: 281 lines, 14x if_exists="ignore", conditional OpenAI blocks.
"""

import os

import pixeltable as pxt
from pixeltable.functions import image as pxt_image
from pixeltable.functions.audio import audio_splitter
from pixeltable.functions.document import document_splitter
from pixeltable.functions.huggingface import clip, sentence_transformer
from pixeltable.functions.string import string_splitter
from pixeltable.functions.uuid import uuid7
from pixeltable.functions.video import extract_audio, frame_iterator

from pxt_declarative import Column, EmbeddingIndex, Model, ViewModel, create_all

text_embed = sentence_transformer.using(model_id="all-MiniLM-L6-v2")
clip_embed = clip.using(model_id="openai/clip-vit-base-patch32")

HAS_OPENAI = bool(os.environ.get("OPENAI_API_KEY"))
if HAS_OPENAI:
    from pixeltable.functions import openai


# ============================= DOCUMENTS =====================================

class Documents(Model):
    __tablename__ = "kb.documents"
    __primary_key__ = ["id"]
    id: pxt.String = uuid7()
    doc: pxt.Document


class DocChunks(ViewModel):
    __tablename__ = "kb.doc_chunks"
    __base__ = document_splitter(Documents.doc, separators="token_limit", limit=300)
    __indexes__ = [
        EmbeddingIndex(Column.text, idx_name="doc_text_idx",
                       string_embed=text_embed, metric="cosine")
    ]


# ============================= IMAGES ========================================

class Images(Model):
    __tablename__ = "kb.images"
    __primary_key__ = ["id"]
    id: pxt.String = uuid7()
    image: pxt.Image
    caption: pxt.String
    thumbnail = pxt_image.thumbnail(Column.image, size=(320, 320))
    __indexes__ = [
        EmbeddingIndex(Column.image, idx_name="image_clip_idx",
                       embedding=clip_embed, metric="cosine")
    ]


# ============================= VIDEO =========================================

class Videos(Model):
    __tablename__ = "kb.videos"
    __primary_key__ = ["id"]
    id: pxt.String = uuid7()
    video: pxt.Video
    audio_track = extract_audio(Column.video, format="wav")


class VideoFrames(ViewModel):
    __tablename__ = "kb.video_frames"
    __base__ = frame_iterator(Videos.video, fps=1.0)
    __indexes__ = [
        EmbeddingIndex(Column.frame, idx_name="frame_clip_idx",
                       embedding=clip_embed, metric="cosine")
    ]


class VideoAudioSegments(ViewModel):
    __tablename__ = "kb.video_audio_segments"
    __base__ = audio_splitter(Videos.audio_track, duration=30.0, overlap=2.0)


if HAS_OPENAI:
    VideoAudioSegments.register_column(
        "transcription",
        openai.transcriptions(Column.audio_segment, model="whisper-1"),
    )
    VideoAudioSegments.register_column(
        "transcript_text",
        Column.transcription.text.astype(pxt.String),
    )

    class VideoTranscriptSentences(ViewModel):
        __tablename__ = "kb.video_transcript_sentences"
        __parent__ = VideoAudioSegments
        __filter__ = Column.transcript_text != None
        __iterator__ = string_splitter(
            VideoAudioSegments.transcript_text, separators="sentence"
        )
        __indexes__ = [
            EmbeddingIndex(Column.text, idx_name="video_transcript_idx",
                           string_embed=text_embed, metric="cosine")
        ]


# ============================= AUDIO =========================================

class AudioFiles(Model):
    __tablename__ = "kb.audio_files"
    __primary_key__ = ["id"]
    id: pxt.String = uuid7()
    audio: pxt.Audio


class AudioSegments(ViewModel):
    __tablename__ = "kb.audio_segments"
    __base__ = audio_splitter(AudioFiles.audio, duration=30.0, overlap=2.0)


if HAS_OPENAI:
    AudioSegments.register_column(
        "transcription",
        openai.transcriptions(Column.audio_segment, model="whisper-1"),
    )
    AudioSegments.register_column(
        "transcript_text",
        Column.transcription.text.astype(pxt.String),
    )

    class AudioTranscriptSentences(ViewModel):
        __tablename__ = "kb.audio_transcript_sentences"
        __parent__ = AudioSegments
        __filter__ = Column.transcript_text != None
        __iterator__ = string_splitter(
            AudioSegments.transcript_text, separators="sentence"
        )
        __indexes__ = [
            EmbeddingIndex(Column.text, idx_name="audio_transcript_idx",
                           string_embed=text_embed, metric="cosine")
        ]


# ============================= QUERIES =======================================

@pxt.query
def search_documents(query_text: str, n: int = 10) -> pxt.Query:
    t = DocChunks._pxt_table or pxt.get_table("kb.doc_chunks")
    sim = t.text.similarity(string=query_text)
    return t.select(t.text, source=t.doc, sim=sim).order_by(sim, asc=False).limit(n)


@pxt.query
def search_images(query_text: str, n: int = 10) -> pxt.Query:
    t = Images._pxt_table or pxt.get_table("kb.images")
    sim = t.image.similarity(string=query_text)
    return t.select(t.image, t.caption, sim=sim).order_by(sim, asc=False).limit(n)


@pxt.query
def search_video_frames(query_text: str, n: int = 10) -> pxt.Query:
    t = VideoFrames._pxt_table or pxt.get_table("kb.video_frames")
    sim = t.frame.similarity(string=query_text)
    return t.select(t.frame, sim=sim).order_by(sim, asc=False).limit(n)


if HAS_OPENAI:
    @pxt.query
    def search_video_transcripts(query_text: str, n: int = 10) -> pxt.Query:
        t = pxt.get_table("kb.video_transcript_sentences")
        sim = t.text.similarity(string=query_text)
        return t.select(t.text, sim=sim).order_by(sim, asc=False).limit(n)

    @pxt.query
    def search_audio_transcripts(query_text: str, n: int = 10) -> pxt.Query:
        t = pxt.get_table("kb.audio_transcript_sentences")
        sim = t.text.similarity(string=query_text)
        return t.select(t.text, sim=sim).order_by(sim, asc=False).limit(n)


# ============================= INIT ==========================================

create_all("kb", checkfirst=True)

if __name__ == "__main__":
    print("Schema initialized. Run: python app.py")
