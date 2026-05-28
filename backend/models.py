from datetime import datetime
from typing import Any

import config
from pydantic import BaseModel


class ToolAgentRow(BaseModel):
    prompt: str
    conversation_id: str = "default"
    timestamp: datetime
    initial_system_prompt: str = config.INITIAL_SYSTEM_PROMPT
    final_system_prompt: str = config.FINAL_SYSTEM_PROMPT
    max_tokens: int = config.DEFAULT_MAX_TOKENS
    temperature: float = config.DEFAULT_TEMPERATURE


class ChatHistoryRow(BaseModel):
    role: str
    content: str
    conversation_id: str
    timestamp: datetime


class AgentResult(BaseModel):
    model_config = {"extra": "ignore"}
    answer: str | None = None
    doc_context: Any = None
    image_context: Any = None
    tool_output: Any = None


class QueryRequest(BaseModel):
    query: str
    conversation_id: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    system_prompt: str | None = None


class QueryMetadata(BaseModel):
    timestamp: str
    has_doc_context: bool
    has_image_context: bool
    has_tool_output: bool


class QueryResponse(BaseModel):
    answer: str
    metadata: QueryMetadata
