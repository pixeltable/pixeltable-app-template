"""Backend setup_pixeltable -- class-based declarative schema.

Equivalent to backend/setup_pixeltable.py.
Original: 329 lines, 22x if_exists="ignore", 11-step agent pipeline.
"""

import os

import pixeltable as pxt
from pixeltable.functions import image as pxt_image, openai, string as pxt_str
from pixeltable.functions.anthropic import invoke_tools, messages
from pixeltable.functions.audio import audio_splitter
from pixeltable.functions.document import document_splitter
from pixeltable.functions.huggingface import sentence_transformer, clip
from pixeltable.functions.string import string_splitter
from pixeltable.functions.uuid import uuid7
from pixeltable.functions.video import extract_audio, frame_iterator

import config
import functions
from pxt_declarative import Column, EmbeddingIndex, Model, ViewModel, create_all

if os.getenv("RESET_SCHEMA", "false").lower() == "true":
    pxt.drop_dir(config.APP_NAMESPACE, force=True)

ns = config.APP_NAMESPACE
sentence_embed = sentence_transformer.using(model_id=config.EMBEDDING_MODEL_ID)
clip_embed = clip.using(model_id=config.CLIP_MODEL_ID)


# ═══════════════════════════════════════════════════════════════════════════════
# Document pipeline
# ═══════════════════════════════════════════════════════════════════════════════

class Documents(Model):
    __tablename__ = f"{ns}.documents"
    __primary_key__ = ["uuid"]
    document: pxt.Document
    uuid: pxt.String = uuid7()
    timestamp: pxt.Timestamp


class Chunks(ViewModel):
    __tablename__ = f"{ns}.chunks"
    __base__ = document_splitter(
        document=Documents.document,
        separators="page, sentence",
        metadata="title, heading, page",
    )
    __indexes__ = [
        EmbeddingIndex(Column.text, idx_name="chunks_text_embed",
                       string_embed=sentence_embed)
    ]


@pxt.query
def _search_documents(query_text: str):
    sim = chunks.text.similarity(string=query_text)
    return (chunks.where((sim > 0.5) & (pxt_str.len(chunks.text) > 30))
            .order_by(sim, asc=False)
            .select(chunks.text, source_doc=chunks.document, sim=sim,
                    title=chunks.title, heading=chunks.heading,
                    page_number=chunks.page)
            .limit(20))


# ═══════════════════════════════════════════════════════════════════════════════
# Image pipeline
# ═══════════════════════════════════════════════════════════════════════════════

class Images(Model):
    __tablename__ = f"{ns}.images"
    __primary_key__ = ["uuid"]
    image: pxt.Image
    uuid: pxt.String = uuid7()
    timestamp: pxt.Timestamp
    thumbnail = pxt_image.b64_encode(
        pxt_image.thumbnail(Column.image, size=(320, 320)))
    __indexes__ = [
        EmbeddingIndex(Column.image, idx_name="images_clip_embed",
                       embedding=clip_embed)
    ]


@pxt.query
def _search_images(query_text: str):
    sim = images.image.similarity(string=query_text)
    return (images.where(sim > 0.25).order_by(sim, asc=False)
            .select(encoded_image=pxt_image.b64_encode(
                        pxt_image.thumbnail(images.image, size=(224, 224)), "png"),
                    sim=sim)
            .limit(5))


# ═══════════════════════════════════════════════════════════════════════════════
# Video pipeline
# ═══════════════════════════════════════════════════════════════════════════════

class Videos(Model):
    __tablename__ = f"{ns}.videos"
    __primary_key__ = ["uuid"]
    video: pxt.Video
    uuid: pxt.String = uuid7()
    timestamp: pxt.Timestamp
    audio = extract_audio(Column.video, format="mp3")


class VideoFrames(ViewModel):
    __tablename__ = f"{ns}.video_frames"
    __base__ = frame_iterator(video=Videos.video, keyframes_only=True)
    frame_thumbnail = pxt_image.b64_encode(
        pxt_image.thumbnail(Column.frame, size=(320, 320)))
    __indexes__ = [
        EmbeddingIndex(Column.frame, idx_name="frames_clip_embed",
                       embedding=clip_embed)
    ]


@pxt.query
def _search_video_frames(query_text: str):
    sim = video_frames.frame.similarity(string=query_text)
    return (video_frames.where(sim > 0.25).order_by(sim, asc=False)
            .select(encoded_frame=pxt_image.b64_encode(video_frames.frame, "png"),
                    source_video=video_frames.video, sim=sim)
            .limit(5))


class VideoAudioChunks(ViewModel):
    __tablename__ = f"{ns}.video_audio_chunks"
    __base__ = audio_splitter(audio=Videos.audio, duration=30.0)
    transcription = openai.transcriptions(
        audio=Column.audio_segment, model=config.WHISPER_MODEL_ID)


class VideoSentences(ViewModel):
    __tablename__ = f"{ns}.video_sentences"
    __parent__ = VideoAudioChunks
    __filter__ = Column.transcription != None
    __iterator__ = string_splitter(
        text=VideoAudioChunks.transcription.text, separators="sentence")
    __indexes__ = [
        EmbeddingIndex(Column.text, idx_name="sentences_text_embed",
                       string_embed=sentence_embed)
    ]


@pxt.query
def _search_video_transcripts(query_text: str):
    sim = video_sentences.text.similarity(string=query_text)
    return (video_sentences.where(sim > 0.7).order_by(sim, asc=False)
            .select(video_sentences.text, source_video=video_sentences.video,
                    sim=sim)
            .limit(20))


# ═══════════════════════════════════════════════════════════════════════════════
# Chat history
# ═══════════════════════════════════════════════════════════════════════════════

class ChatHistory(Model):
    __tablename__ = f"{ns}.chat_history"
    role: pxt.String
    content: pxt.String
    conversation_id: pxt.String
    timestamp: pxt.Timestamp
    __indexes__ = [
        EmbeddingIndex(Column.content, idx_name="chat_content_embed",
                       string_embed=sentence_embed)
    ]


@pxt.query
def _get_recent_chat_history(conversation_id: str, limit: int = 4):
    t = pxt.get_table(f"{ns}.chat_history")
    return (t.where(t.conversation_id == conversation_id)
            .order_by(t.timestamp, asc=False)
            .select(role=t.role, content=t.content).limit(limit))


@pxt.query
def _search_chat_history(query_text: str):
    t = pxt.get_table(f"{ns}.chat_history")
    sim = t.content.similarity(string=query_text)
    return (t.where(sim > 0.8).order_by(sim, asc=False)
            .select(role=t.role, content=t.content, sim=sim).limit(10))


# ═══════════════════════════════════════════════════════════════════════════════
# Agent pipeline -- 11-step computed column chain
# ═══════════════════════════════════════════════════════════════════════════════

tools = pxt.tools(functions.web_search, _search_documents, _search_video_transcripts)


class AgentPipeline(Model):
    __tablename__ = f"{ns}.agent"
    prompt: pxt.String
    conversation_id: pxt.String
    timestamp: pxt.Timestamp
    initial_system_prompt: pxt.String
    final_system_prompt: pxt.String
    max_tokens: pxt.Int
    temperature: pxt.Float

    initial_response = messages(
        model=config.CLAUDE_MODEL_ID,
        messages=[{"role": "user", "content": Column.prompt}],
        tools=tools,
        tool_choice=tools.choice(required=True),
        max_tokens=Column.max_tokens,
        model_kwargs={"system": Column.initial_system_prompt,
                      "temperature": Column.temperature},
    )
    tool_output = invoke_tools(tools, Column.initial_response)
    doc_context = _search_documents(Column.prompt)
    image_context = _search_images(Column.prompt)
    video_frame_context = _search_video_frames(Column.prompt)
    chat_memory_context = _search_chat_history(Column.prompt)
    history_context = _get_recent_chat_history(Column.conversation_id)
    multimodal_context = functions.assemble_context(
        Column.prompt, Column.tool_output,
        Column.doc_context, Column.chat_memory_context)
    final_messages = functions.assemble_final_messages(
        Column.history_context, Column.multimodal_context,
        image_context=Column.image_context,
        video_frame_context=Column.video_frame_context)
    final_response = messages(
        model=config.CLAUDE_MODEL_ID,
        messages=Column.final_messages,
        max_tokens=Column.max_tokens,
        model_kwargs={"system": Column.final_system_prompt,
                      "temperature": Column.temperature},
    )
    answer = Column.final_response.content[0].text


# ═══════════════════════════════════════════════════════════════════════════════
# Initialization
# ═══════════════════════════════════════════════════════════════════════════════

create_all(ns, checkfirst=True)

if __name__ == "__main__":
    print("Schema setup complete.")
