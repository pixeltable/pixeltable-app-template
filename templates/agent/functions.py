"""UDFs for the agent pipeline."""

from typing import Any

import pixeltable as pxt


@pxt.udf
def web_search(query: str) -> str:
    """Web search stub -- replace with your preferred search API (e.g. DuckDuckGo, Brave, Tavily)."""
    return f'[web_search placeholder] No results for: {query}'


@pxt.udf
def assemble_context(
    prompt: str,
    memory_context: list[dict[str, Any]] | None,
    knowledge_context: list[Any] | None,
    tool_output: list[dict[str, Any]] | None,
) -> str:
    """Merge memory, knowledge, and tool results into a single context block for the LLM."""
    parts = [f'QUESTION:\n{prompt}']
    if knowledge_context:
        items = [
            item.get('text', str(item)) if isinstance(item, dict) else str(item)
            for item in knowledge_context
        ]
        parts.append('KNOWLEDGE:\n' + '\n'.join(f'- {t}' for t in items if t))
    if memory_context:
        lines = [
            f"- [{m.get('role', '?')}] {m.get('content', '')[:200]}"
            for m in memory_context
        ]
        parts.append('MEMORY:\n' + '\n'.join(lines))
    if tool_output:
        parts.append(f'TOOL RESULTS:\n{tool_output}')
    return '\n\n'.join(parts)
