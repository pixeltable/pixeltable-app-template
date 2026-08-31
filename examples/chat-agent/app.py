"""Knowledge, memory, and the LLM answer are tables and computed columns.

    pxt schema update app.py agent
    pxt service update app.py agent

Requires ANTHROPIC_API_KEY for /ask (and ask()) to produce answers.
"""

# ruff: noqa: F821

from __future__ import annotations

from datetime import datetime
from typing import Any

import pixeltable as pxt
import pixeltable.functions as pxtf
from pixeltable.functions.anthropic import messages
from pixeltable.functions.huggingface import sentence_transformer
from pixeltable.serving import FastAPIRouter

TableModel = pxt.model_base()
embed_fn = sentence_transformer.using(model_id="all-MiniLM-L6-v2")


@pxt.udf
def assemble_context(
    prompt: str,
    memory_context: list[dict[str, Any]] | None,
    knowledge_context: list[Any] | None,
) -> str:
    """Merge memory and knowledge into one context block for the LLM."""
    parts = [f"QUESTION:\n{prompt}"]
    if knowledge_context:
        items = [item.get("text", str(item)) if isinstance(item, dict) else str(item) for item in knowledge_context]
        parts.append("KNOWLEDGE:\n" + "\n".join(f"- {t}" for t in items if t))
    if memory_context:
        lines = [f"- [{m.get('role', '?')}] {m.get('content', '')[:200]}" for m in memory_context]
        parts.append("MEMORY:\n" + "\n".join(lines))
    return "\n\n".join(parts)


class Knowledge(TableModel, name="knowledge"):
    body: pxt.String
    title: pxt.String
    source: pxt.String
    uuid = pxt.Column(value=pxtf.uuid.uuid7(), primary_key=True)
    timestamp: pxt.Timestamp | None


class Sentences(
    TableModel,
    name="sentences",
    base=Knowledge,
    iterator=pxtf.string.string_splitter(Knowledge.body, separators="sentence"),
):
    __indexes__ = [
        pxt.EmbeddingIndex(text, embedding=embed_fn, name="knowledge_embed"),
    ]


class Conversations(TableModel, name="conversations"):
    role: pxt.String
    content: pxt.String
    conversation_id: pxt.String
    user_id: pxt.String
    uuid = pxt.Column(value=pxtf.uuid.uuid7(), primary_key=True)
    timestamp: pxt.Timestamp | None
    __indexes__ = [
        pxt.EmbeddingIndex(content, embedding=embed_fn, name="conversations_embed"),
    ]


@pxt.query
def search_knowledge(query_text: str, limit: int = 10) -> pxt.Query:
    """Semantic search over the knowledge base."""
    sim = Sentences.text.similarity(string=query_text)
    return Sentences.where(sim > 0.3).order_by(sim, asc=False).select(Sentences.text, score=sim).limit(limit)


@pxt.query
def recall_memory(query_text: str, limit: int = 10) -> pxt.Query:
    """Semantic recall across conversations."""
    sim = Conversations.content.similarity(string=query_text)
    return (
        Conversations.where(sim > 0.5)
        .order_by(sim, asc=False)
        .select(
            role=Conversations.role,
            content=Conversations.content,
            conversation_id=Conversations.conversation_id,
            score=sim,
        )
        .limit(limit)
    )


@pxt.query
def get_history(conversation_id: str, limit: int = 10) -> pxt.Query:
    """Recent turns from one conversation."""
    return (
        Conversations.where(Conversations.conversation_id == conversation_id)
        .order_by(Conversations.timestamp, asc=False)
        .select(
            role=Conversations.role,
            content=Conversations.content,
            timestamp=Conversations.timestamp,
        )
        .limit(limit)
    )


class Agent(TableModel, name="agent"):
    prompt: pxt.String
    conversation_id: pxt.String
    system_prompt: pxt.String
    max_tokens: pxt.Int
    temperature: pxt.Float
    uuid = pxt.Column(value=pxtf.uuid.uuid7(), primary_key=True)
    timestamp: pxt.Timestamp | None
    memory_context = recall_memory(prompt)
    knowledge_context = search_knowledge(prompt)
    context = assemble_context(prompt, memory_context, knowledge_context)
    final_response = messages(
        messages=[{"role": "user", "content": context}],
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        model_kwargs={
            "system": system_prompt,
            "temperature": temperature,
        },
    )
    answer = final_response.content[0].text


api = FastAPIRouter(name="agent", prefix="/api")
api.add_insert_route(
    Agent,
    path="/ask",
    inputs=[Agent.prompt, Agent.conversation_id, Agent.system_prompt, Agent.max_tokens, Agent.temperature],
    outputs=[Agent.uuid, Agent.answer],
)
api.add_insert_route(
    Knowledge,
    path="/knowledge",
    inputs=[Knowledge.body, Knowledge.title, Knowledge.source],
    outputs=[Knowledge.uuid],
)
api.add_insert_route(
    Conversations,
    path="/conversations",
    inputs=[Conversations.role, Conversations.content, Conversations.conversation_id, Conversations.user_id],
    outputs=[Conversations.uuid],
)
api.add_query_route(path="/knowledge/search", query=search_knowledge, method="get")
api.add_query_route(path="/memory/search", query=recall_memory, method="get")
api.add_query_route(path="/history", query=get_history, method="get")


def ask(
    question: str,
    conversation_id: str = "default",
    *,
    system_prompt: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.7,
) -> str:
    """Insert a prompt, return the answer, and append turns to conversation memory."""
    agent_tbl = pxt.get_table("agent.agent", if_not_exists="ignore")
    conversations_tbl = pxt.get_table("agent.conversations", if_not_exists="ignore")
    if agent_tbl is None or conversations_tbl is None:
        raise RuntimeError("Tables not materialized. Run: pxt schema update app.py agent")

    ts = datetime.now()
    sys_prompt = system_prompt or (
        "You are a helpful assistant with a knowledge base and conversation memory. Be concise and accurate."
    )
    agent_tbl.insert(
        [
            {
                "prompt": question,
                "conversation_id": conversation_id,
                "system_prompt": sys_prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "timestamp": ts,
            }
        ]
    )

    result = (
        agent_tbl.where(agent_tbl.timestamp == ts)
        .order_by(agent_tbl.timestamp, asc=False)
        .limit(1)
        .select(agent_tbl.answer)
        .collect()
    )
    if not result:
        return "Error: no response generated."

    answer = result[0].get("answer") or "Error: no answer in response."
    conversations_tbl.insert(
        [
            {
                "role": "user",
                "content": question,
                "conversation_id": conversation_id,
                "user_id": "default",
                "timestamp": ts,
            },
            {
                "role": "assistant",
                "content": answer,
                "conversation_id": conversation_id,
                "user_id": "system",
                "timestamp": datetime.now(),
            },
        ]
    )
    return answer
