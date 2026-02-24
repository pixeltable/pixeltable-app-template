"""User-Defined Functions (UDFs) for the Pixeltable App Template."""
import os
from typing import Optional, Dict, Any, List, Union

import pixeltable as pxt


@pxt.udf
def web_search(keywords: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo (no API key required)."""
    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(
                ddgs.news(
                    keywords=keywords,
                    region="wt-wt",
                    safesearch="off",
                    timelimit="m",
                    max_results=max_results,
                )
            )
            if not results:
                return "No results found."

            formatted = []
            for i, r in enumerate(results, 1):
                formatted.append(
                    f"{i}. {r.get('title', 'N/A')}\n"
                    f"   Source: {r.get('source', 'N/A')}\n"
                    f"   URL: {r.get('url', 'N/A')}\n"
                    f"   {r.get('body', 'N/A')}\n"
                )
            return "\n".join(formatted)
    except Exception as e:
        return f"Search failed: {str(e)}."


@pxt.udf
def extract_document_text(doc: pxt.Document) -> Optional[str]:
    """Extract full text from a document file, truncated for downstream use."""
    import pathlib

    try:
        path = pathlib.Path(doc)
        ext = path.suffix.lower()
        text = ""

        if ext == ".pdf":
            import pdfplumber

            with pdfplumber.open(str(path)) as pdf:
                pages = [page.extract_text() or "" for page in pdf.pages]
                text = "\n".join(pages)
        elif ext in (".txt", ".md", ".html", ".xml", ".rtf", ".csv"):
            text = path.read_text(errors="ignore")
        else:
            text = path.read_text(errors="ignore")

        if not text or not text.strip():
            return None

        max_chars = 15_000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n...[truncated]"

        return text.strip()
    except Exception as e:
        return f"[Error extracting text: {str(e)}]"


@pxt.udf
def assemble_context(
    question: str,
    tool_outputs: Optional[List[Dict[str, Any]]],
    doc_context: Optional[List[Union[Dict[str, Any], str]]],
    chat_memory_context: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Combine all context sources into a single text block for the LLM."""
    doc_context_str = "N/A"
    if doc_context:
        items = []
        for item in doc_context:
            text = item.get("text", "") if isinstance(item, dict) else str(item)
            source = (
                item.get("source_doc", "Unknown")
                if isinstance(item, dict)
                else "Unknown"
            )
            source_name = os.path.basename(str(source))
            if text:
                items.append(f"- [Source: {source_name}] {text}")
        if items:
            doc_context_str = "\n".join(items)

    chat_str = "N/A"
    if chat_memory_context:
        chat_items = []
        for item in chat_memory_context:
            content = item.get("content", "")
            role = item.get("role", "unknown")
            chat_items.append(f"- [{role}] {content[:150]}")
        if chat_items:
            chat_str = "\n".join(chat_items)

    tool_str = str(tool_outputs) if tool_outputs else "N/A"

    return f"""ORIGINAL QUESTION:
{question}

AVAILABLE CONTEXT:

[TOOL RESULTS]
{tool_str}

[DOCUMENT CONTEXT]
{doc_context_str}

[CHAT HISTORY CONTEXT]
{chat_str}""".strip()


@pxt.udf
def assemble_final_messages(
    history_context: Optional[List[Dict[str, Any]]],
    multimodal_context_text: str,
    image_context: Optional[List[Dict[str, Any]]] = None,
    video_frame_context: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Build the final message list for the LLM, incorporating all context."""
    msgs: List[Dict[str, Any]] = []

    if history_context:
        for item in reversed(history_context):
            role = item.get("role")
            content = item.get("content")
            if role and content:
                msgs.append({"role": role, "content": content})

    final_user_content: List[Dict[str, Any]] = []

    if image_context:
        for item in image_context:
            if isinstance(item, dict) and "encoded_image" in item:
                data = item["encoded_image"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                elif not isinstance(data, str):
                    continue
                final_user_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": data,
                    },
                })

    if video_frame_context:
        for item in video_frame_context:
            if isinstance(item, dict) and "encoded_frame" in item:
                data = item["encoded_frame"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                elif not isinstance(data, str):
                    continue
                final_user_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": data,
                    },
                })

    final_user_content.append({"type": "text", "text": multimodal_context_text})
    msgs.append({"role": "user", "content": final_user_content})
    return msgs
