"""UDFs for the content processing pipeline."""

import pixeltable as pxt


@pxt.udf
def get_processing_status() -> dict:
    """Count of items per modality."""
    media = pxt.get_table('pipeline.media')
    images = pxt.get_table('pipeline.images')
    documents = pxt.get_table('pipeline.documents')
    audio_files = pxt.get_table('pipeline.audio_files')
    doc_chunks = pxt.get_view('pipeline.doc_chunks')
    return {
        'images': images.count(),
        'documents': documents.count(),
        'audio_files': audio_files.count(),
        'media_total': media.count(),
        'doc_chunks': doc_chunks.count(),
    }
