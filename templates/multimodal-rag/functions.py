"""UDFs for the multimodal RAG pipeline."""

import pixeltable as pxt


@pxt.udf
def merge_results(*result_lists: list[dict]) -> list[dict]:
    """Merge and deduplicate ranked results from multiple modality searches."""
    merged: list[dict] = []
    seen_texts: set[str] = set()
    for results in result_lists:
        if results is None:
            continue
        for r in results:
            text_key = str(r.get("text", r.get("caption", "")))[:200]
            if text_key and text_key in seen_texts:
                continue
            seen_texts.add(text_key)
            merged.append(r)
    merged.sort(key=lambda r: r.get("sim", 0), reverse=True)
    return merged
