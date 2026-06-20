"""Chat Agent -- class-based declarative schema.

Equivalent to templates/chat-agent/schema.py.
Original: 245 lines, 13x if_exists="ignore", conditional Anthropic blocks.
"""

import os
from datetime import datetime

import functions
import pixeltable as pxt
from pixeltable.functions.huggingface import sentence_transformer
from pixeltable.functions.string import string_splitter
from pixeltable.functions.uuid import uuid7

from pxt_declarative import Column, EmbeddingIndex, Model, ViewModel, create_all

HAS_ANTHROPIC = bool(os.getenv("ANTHROPIC_API_KEY"))
if HAS_ANTHROPIC:
    from pixeltable.functions.anthropic import invoke_tools, messages

embed_fn = sentence_transformer.using(model_id="all-MiniLM-L6-v2")


# ── Knowledge base ──────────────────────────────────────────────────────────

class Knowledge(Model):
    __tablename__ = "agent.knowledge"
    __primary_key__ = ["uuid"]
    text: pxt.String
    title: pxt.String
    source: pxt.String
    uuid: pxt.String = uuid7()
    timestamp: pxt.Timestamp


class Sentences(ViewModel):
    __tablename__ = "agent.sentences"
    __base__ = string_splitter(text=Knowledge.text, separators="sentence")
    __indexes__ = [
        EmbeddingIndex(Column.text, idx_name="knowledge_embed",
                       string_embed=embed_fn)
    ]


# ── Conversations / memory ──────────────────────────────────────────────────

class Conversations(Model):
    __tablename__ = "agent.conversations"
    __primary_key__ = ["uuid"]
    role: pxt.String
    content: pxt.String
    conversation_id: pxt.String
    user_id: pxt.String
    uuid: pxt.String = uuid7()
    timestamp: pxt.Timestamp
    __indexes__ = [
        EmbeddingIndex(Column.content, idx_name="conversations_embed",
                       string_embed=embed_fn)
    ]


# ── Agent table ─────────────────────────────────────────────────────────────

class Agent(Model):
    __tablename__ = "agent.agent"
    __primary_key__ = ["uuid"]
    prompt: pxt.String
    conversation_id: pxt.String
    system_prompt: pxt.String
    max_tokens: pxt.Int
    temperature: pxt.Float
    uuid: pxt.String = uuid7()
    timestamp: pxt.Timestamp


# ── Query functions ─────────────────────────────────────────────────────────

@pxt.query
def search_knowledge(query_text: str, limit: int = 10):
    t = pxt.get_table("agent.sentences")
    sim = t.text.similarity(string=query_text)
    return (t.where(sim > 0.3).order_by(sim, asc=False)
            .select(t.text, title=t.title, sim=sim).limit(limit))


@pxt.query
def recall_memory(query_text: str, limit: int = 10):
    t = pxt.get_table("agent.conversations")
    sim = t.content.similarity(string=query_text)
    return (t.where(sim > 0.5).order_by(sim, asc=False)
            .select(role=t.role, content=t.content,
                    conversation_id=t.conversation_id, sim=sim)
            .limit(limit))


@pxt.query
def get_history(conversation_id: str, limit: int = 10):
    t = pxt.get_table("agent.conversations")
    return (t.where(t.conversation_id == conversation_id)
            .order_by(t.timestamp, asc=False)
            .select(role=t.role, content=t.content, timestamp=t.timestamp)
            .limit(limit))


# ── LLM pipeline (conditional) ──────────────────────────────────────────────

if HAS_ANTHROPIC:
    tools = pxt.tools(functions.web_search, search_knowledge, recall_memory)

    Agent.register_column("memory_context", recall_memory(Column.prompt))
    Agent.register_column("knowledge_context", search_knowledge(Column.prompt))
    Agent.register_column("initial_response", messages(
        model="claude-sonnet-4-20250514",
        messages=[{"role": "user", "content": Column.prompt}],
        tools=tools,
        tool_choice=tools.choice(required=True),
        max_tokens=Column.max_tokens,
        model_kwargs={
            "system": Column.system_prompt,
            "temperature": Column.temperature,
        },
    ))
    Agent.register_column("tool_output", invoke_tools(tools, Column.initial_response))
    Agent.register_column("context", functions.assemble_context(
        Column.prompt, Column.memory_context,
        Column.knowledge_context, Column.tool_output,
    ))
    Agent.register_column("final_response", messages(
        model="claude-sonnet-4-20250514",
        messages=[{"role": "user", "content": Column.context}],
        max_tokens=Column.max_tokens,
        model_kwargs={
            "system": Column.system_prompt,
            "temperature": Column.temperature,
        },
    ))
    Agent.register_column("answer", Column.final_response.content[0].text)


# ── Initialization ──────────────────────────────────────────────────────────

create_all("agent", checkfirst=True)


# ── Main agent endpoint ─────────────────────────────────────────────────────

def ask(question: str, conversation_id: str = "default") -> str:
    if not HAS_ANTHROPIC:
        return "Error: set ANTHROPIC_API_KEY to enable the agent pipeline."

    ts = datetime.now()
    agent_tbl = pxt.get_table("agent.agent")
    agent_tbl.insert([{
        "prompt": question,
        "conversation_id": conversation_id,
        "system_prompt": (
            "You are a helpful assistant with access to tools, a knowledge base, "
            "and conversation memory. Use tools when needed. Be concise and accurate."
        ),
        "max_tokens": 1024,
        "temperature": 0.7,
        "timestamp": ts,
    }])

    result = (agent_tbl.where(agent_tbl.timestamp == ts)
              .order_by(agent_tbl.timestamp, asc=False).limit(1)
              .select(agent_tbl.answer).collect())
    if not result:
        return "Error: no response generated."

    answer = result[0].get("answer", "Error: no answer in response.")
    conv_tbl = pxt.get_table("agent.conversations")
    conv_tbl.insert([
        {"role": "user", "content": question, "conversation_id": conversation_id,
         "user_id": "default", "timestamp": ts},
        {"role": "assistant", "content": answer, "conversation_id": conversation_id,
         "user_id": "system", "timestamp": datetime.now()},
    ])
    return answer


if __name__ == "__main__":
    print("Schema initialized. Run: python app.py")
