"""UDFs for the audio intelligence pipeline."""

import pixeltable as pxt


@pxt.udf
def generate_full_summary(chunk_summaries: list[str]) -> str:
    """Concatenate chunk summaries into a single episode overview."""
    return '\n\n'.join(s for s in chunk_summaries if s)
