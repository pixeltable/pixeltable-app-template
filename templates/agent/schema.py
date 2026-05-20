"""Persistent multimodal agent — everything is a table.

Replaces Mem0/MemGPT: conversations, memory, knowledge, and tool traces
are all queryable, versioned Pixeltable tables.

    python app.py           # start the server with web UI
    # or API-only: python schema.py && pxt serve agent
"""

import os
from datetime import datetime

import functions
import pixeltable as pxt
from pixeltable.functions.huggingface import sentence_transformer
from pixeltable.functions.string import string_splitter
from pixeltable.functions.uuid import uuid7

HAS_ANTHROPIC = bool(os.getenv("ANTHROPIC_API_KEY"))
if HAS_ANTHROPIC:
    from pixeltable.functions.anthropic import invoke_tools, messages

pxt.create_dir("agent", if_exists="ignore")

embed_fn = sentence_transformer.using(model_id="all-MiniLM-L6-v2")

# ── Knowledge base ────────────────────────────────────────────────────────

knowledge = pxt.create_table(
    "agent.knowledge",
    {
        "text": pxt.String,
        "title": pxt.String,
        "source": pxt.String,
        "uuid": uuid7(),
        "timestamp": pxt.Timestamp,
    },
    primary_key=["uuid"],
    if_exists="ignore",
)

sentences = pxt.create_view(
    "agent.sentences",
    knowledge,
    iterator=string_splitter(text=knowledge.text, separators="sentence"),
    if_exists="ignore",
)
sentences.add_embedding_index("text", idx_name="knowledge_embed", string_embed=embed_fn, if_exists="ignore")

# ── Conversations / memory ────────────────────────────────────────────────

conversations = pxt.create_table(
    "agent.conversations",
    {
        "role": pxt.String,
        "content": pxt.String,
        "conversation_id": pxt.String,
        "user_id": pxt.String,
        "uuid": uuid7(),
        "timestamp": pxt.Timestamp,
    },
    primary_key=["uuid"],
    if_exists="ignore",
)
conversations.add_embedding_index("content", idx_name="conversations_embed", string_embed=embed_fn, if_exists="ignore")

# ── Query functions ───────────────────────────────────────────────────────


@pxt.query
def search_knowledge(query_text: str, limit: int = 10):
    """Semantic search over the knowledge base."""
    sim = sentences.text.similarity(string=query_text)
    return (
        sentences.where(sim > 0.3)
        .order_by(sim, asc=False)
        .select(sentences.text, title=sentences.title, sim=sim)
        .limit(limit)
    )


@pxt.query
def recall_memory(query_text: str, limit: int = 10):
    """Semantic recall across all conversations — long-term memory."""
    sim = conversations.content.similarity(string=query_text)
    return (
        conversations.where(sim > 0.5)
        .order_by(sim, asc=False)
        .select(
            role=conversations.role,
            content=conversations.content,
            conversation_id=conversations.conversation_id,
            sim=sim,
        )
        .limit(limit)
    )


@pxt.query
def get_history(conversation_id: str, limit: int = 10):
    """Recent turns from a specific conversation."""
    return (
        conversations.where(conversations.conversation_id == conversation_id)
        .order_by(conversations.timestamp, asc=False)
        .select(
            role=conversations.role,
            content=conversations.content,
            timestamp=conversations.timestamp,
        )
        .limit(limit)
    )


# ── Tools ─────────────────────────────────────────────────────────────────

# Load tools from any MCP-compliant server:
# mcp_tools = pxt.mcp_udfs('http://localhost:8000/mcp')
# tools = pxt.tools(functions.web_search, search_knowledge, recall_memory, *mcp_tools)

# ── Agent table (always created so pxt serve can register routes) ─────────

agent = pxt.create_table(
    "agent.agent",
    {
        "prompt": pxt.String,
        "conversation_id": pxt.String,
        "system_prompt": pxt.String,
        "max_tokens": pxt.Int,
        "temperature": pxt.Float,
        "uuid": uuid7(),
        "timestamp": pxt.Timestamp,
    },
    primary_key=["uuid"],
    if_exists="ignore",
)

# ── LLM pipeline (requires ANTHROPIC_API_KEY) ────────────────────────────

if HAS_ANTHROPIC:
    tools = pxt.tools(functions.web_search, search_knowledge, recall_memory)

    agent.add_computed_column(memory_context=recall_memory(agent.prompt), if_exists="ignore")
    agent.add_computed_column(knowledge_context=search_knowledge(agent.prompt), if_exists="ignore")
    agent.add_computed_column(
        initial_response=messages(
            model="claude-sonnet-4-20250514",
            messages=[{"role": "user", "content": agent.prompt}],
            tools=tools,
            tool_choice=tools.choice(required=True),
            max_tokens=agent.max_tokens,
            model_kwargs={
                "system": agent.system_prompt,
                "temperature": agent.temperature,
            },
        ),
        if_exists="ignore",
    )
    agent.add_computed_column(
        tool_output=invoke_tools(tools, agent.initial_response),
        if_exists="ignore",
    )
    agent.add_computed_column(
        context=functions.assemble_context(
            agent.prompt,
            agent.memory_context,
            agent.knowledge_context,
            agent.tool_output,
        ),
        if_exists="ignore",
    )
    agent.add_computed_column(
        final_response=messages(
            model="claude-sonnet-4-20250514",
            messages=[{"role": "user", "content": agent.context}],
            max_tokens=agent.max_tokens,
            model_kwargs={
                "system": agent.system_prompt,
                "temperature": agent.temperature,
            },
        ),
        if_exists="ignore",
    )
    agent.add_computed_column(answer=agent.final_response.content[0].text, if_exists="ignore")


# ── Main agent endpoint ──────────────────────────────────────────────────


def ask(question: str, conversation_id: str = "default") -> str:
    """Insert prompt → computed column chain → answer. Saves to conversation history."""
    if not HAS_ANTHROPIC:
        return "Error: set ANTHROPIC_API_KEY to enable the agent pipeline."

    ts = datetime.now()
    agent_tbl = pxt.get_table("agent.agent")
    agent_tbl.insert(
        [
            {
                "prompt": question,
                "conversation_id": conversation_id,
                "system_prompt": (
                    "You are a helpful assistant with access to tools, a knowledge base, "
                    "and conversation memory. Use tools when needed. Be concise and accurate."
                ),
                "max_tokens": 1024,
                "temperature": 0.7,
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

    answer = result[0].get("answer", "Error: no answer in response.")
    conversations.insert(
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


if __name__ == "__main__":
    print("Schema initialized. Run: python app.py")
