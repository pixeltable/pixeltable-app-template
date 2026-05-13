"""Tool-calling agent — 1 hand-written endpoint + declarative routes."""

import logging
from datetime import datetime

import pixeltable as pxt
from pixeltable.serving import FastAPIRouter
from fastapi import HTTPException

import config
from models import (
    ToolAgentRow,
    ChatHistoryRow,
    AgentResult,
    QueryRequest,
    QueryMetadata,
    QueryResponse,
)

MAX_QUERY_LENGTH = config.MAX_QUERY_LENGTH

logger = logging.getLogger(__name__)
router = FastAPIRouter(prefix="/api/agent", tags=["agent"])

chat = pxt.get_table(f"{config.APP_NAMESPACE}.chat_history")


@pxt.query
def get_conversation(conversation_id: str):
    return (
        chat.where(chat.conversation_id == conversation_id)
        .select(role=chat.role, content=chat.content, timestamp=chat.timestamp)
        .order_by(chat.timestamp, asc=True)
    )


@pxt.query
def list_messages():
    return chat.select(
        role=chat.role,
        content=chat.content,
        conversation_id=chat.conversation_id,
        timestamp=chat.timestamp,
    ).order_by(chat.timestamp, asc=True)


router.add_query_route(path="/conversation", query=get_conversation, method="post")
router.add_query_route(path="/messages", query=list_messages, method="get")
router.add_delete_route(
    chat, path="/delete-conversation", match_columns=["conversation_id"]
)


@router.post("/query", response_model=QueryResponse)
def query(body: QueryRequest):
    # ── Input guardrail ──────────────────────────────────────────────────
    if not body.query:
        raise HTTPException(status_code=400, detail="Query text is required")
    if len(body.query) > MAX_QUERY_LENGTH:
        raise HTTPException(
            status_code=400, detail=f"Query exceeds {MAX_QUERY_LENGTH} characters"
        )

    try:
        agent_table = pxt.get_table(f"{config.APP_NAMESPACE}.agent")
        ts = datetime.now()
        conversation_id = body.conversation_id or "default"

        # ── Response personalization ─────────────────────────────────────
        row = ToolAgentRow(
            prompt=body.query, conversation_id=conversation_id, timestamp=ts
        )
        if body.temperature is not None:
            row.temperature = body.temperature
        if body.max_tokens is not None:
            row.max_tokens = body.max_tokens
        if body.system_prompt is not None:
            row.final_system_prompt = body.system_prompt

        status = agent_table.insert([row], return_rows=True)

        if not status.rows:
            raise HTTPException(status_code=500, detail="No results after processing")

        result = AgentResult.model_validate(status.rows[0])
        answer = result.answer or "Error: No answer generated."

        try:
            chat.insert(
                [
                    ChatHistoryRow(
                        role="user",
                        content=body.query,
                        conversation_id=conversation_id,
                        timestamp=ts,
                    )
                ]
            )
            if answer and not answer.startswith("Error:"):
                chat.insert(
                    [
                        ChatHistoryRow(
                            role="assistant",
                            content=answer,
                            conversation_id=conversation_id,
                            timestamp=datetime.now(),
                        )
                    ]
                )
        except Exception as e:
            logger.error(f"Error saving chat history: {e}")

        return QueryResponse(
            answer=answer,
            metadata=QueryMetadata(
                timestamp=ts.isoformat(),
                has_doc_context=bool(result.doc_context),
                has_image_context=bool(result.image_context),
                has_tool_output=bool(result.tool_output),
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
