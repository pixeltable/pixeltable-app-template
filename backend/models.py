from datetime import datetime

from pydantic import BaseModel

import config


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
