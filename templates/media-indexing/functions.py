"""Helper functions for the content processing pipeline."""

import pixeltable as pxt


def get_processing_status() -> dict:
    """Count of items per modality."""
    return {
        "images": pxt.get_table("pipeline.images").count(),
        "documents": pxt.get_table("pipeline.documents").count(),
        "audio_files": pxt.get_table("pipeline.audio_files").count(),
        "media_total": pxt.get_table("pipeline.media").count(),
        "doc_chunks": pxt.get_table("pipeline.doc_chunks").count(),
    }
