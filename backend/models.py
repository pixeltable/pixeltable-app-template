from datetime import datetime
from typing import Any

from pydantic import BaseModel

import config


# ── Pixeltable row models ────────────────────────────────────────────────────

class ToolAgentRow(BaseModel):
    """Row model for the app.agent table."""
    prompt: str
    timestamp: datetime
    user_id: str
    initial_system_prompt: str = config.INITIAL_SYSTEM_PROMPT
    final_system_prompt: str = config.FINAL_SYSTEM_PROMPT
    max_tokens: int = config.DEFAULT_MAX_TOKENS
    temperature: float = config.DEFAULT_TEMPERATURE


class ChatHistoryRow(BaseModel):
    """Row model for the app.chat_history table."""
    role: str
    content: str
    conversation_id: str
    timestamp: datetime
    user_id: str


# ── Data endpoint responses ──────────────────────────────────────────────────

class UploadResponse(BaseModel):
    message: str
    filename: str
    uuid: str
    type: str


class FileItem(BaseModel):
    uuid: str
    name: str
    thumbnail: str | None = None
    timestamp: str | None = None


class FilesResponse(BaseModel):
    documents: list[FileItem]
    images: list[FileItem]
    videos: list[FileItem]


class DeleteResponse(BaseModel):
    message: str
    num_deleted: int


class ChunkItem(BaseModel):
    text: str
    title: str | None = None
    heading: str | None = None
    page: int | None = None


class ChunksResponse(BaseModel):
    uuid: str
    chunks: list[ChunkItem]
    total: int


class FrameItem(BaseModel):
    frame: str
    position: float


class FramesResponse(BaseModel):
    uuid: str
    frames: list[FrameItem]
    total: int


class TranscriptionResponse(BaseModel):
    uuid: str
    sentences: list[str]
    full_text: str


# ── Agent conversation responses ─────────────────────────────────────────────

class ConversationSummary(BaseModel):
    conversation_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class ChatMessageItem(BaseModel):
    role: str
    content: str
    timestamp: str


class ConversationDetail(BaseModel):
    conversation_id: str
    messages: list[ChatMessageItem]


# ── Search endpoint responses ────────────────────────────────────────────────

class SearchResult(BaseModel):
    type: str
    uuid: str
    similarity: float
    text: str | None = None
    thumbnail: str | None = None
    metadata: dict[str, Any] | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
