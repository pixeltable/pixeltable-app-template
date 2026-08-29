"""Media indexing application file.

Ingest images, documents, and audio. Chunk, embed, and serve search.

    pxt schema update app.py pipeline
    pxt service update app.py pipeline
    python pipeline.py --urls path/to/file.png
"""

# ruff: noqa: F821

from __future__ import annotations

import pixeltable as pxt
import pixeltable.functions as pxtf
from pixeltable.functions import image as pxt_image
from pixeltable.functions.huggingface import sentence_transformer
from pixeltable.serving import FastAPIRouter

TableModel = pxt.model_base()
embed_fn = sentence_transformer.using(model_id="all-MiniLM-L6-v2")


class Media(TableModel, name="media"):
    url: pxt.String
    media_type: pxt.String
    tags: pxt.Json | None
    uuid = pxt.Column(value=pxtf.uuid.uuid7(), primary_key=True)
    timestamp: pxt.Timestamp | None


class Images(TableModel, name="images"):
    image: pxt.Image
    source_url: pxt.String | None
    uuid = pxt.Column(value=pxtf.uuid.uuid7(), primary_key=True)
    timestamp: pxt.Timestamp | None
    thumbnail = pxt_image.b64_encode(pxt_image.thumbnail(image, size=(320, 320)))
    width = image.width
    height = image.height
    mode = image.mode


class Documents(TableModel, name="documents"):
    document: pxt.Document
    title: pxt.String
    uuid = pxt.Column(value=pxtf.uuid.uuid7(), primary_key=True)
    timestamp: pxt.Timestamp | None


class DocChunks(
    TableModel,
    name="doc_chunks",
    base=Documents,
    iterator=pxtf.document.document_splitter(
        Documents.document,
        separators="sentence,token_limit",
        limit=300,
        metadata="page",
    ),
):
    __indexes__ = [
        pxt.EmbeddingIndex(text, embedding=embed_fn, name="doc_text_idx"),
    ]


class AudioFiles(TableModel, name="audio_files"):
    audio: pxt.Audio
    title: pxt.String
    uuid = pxt.Column(value=pxtf.uuid.uuid7(), primary_key=True)
    timestamp: pxt.Timestamp | None


class AudioChunks(
    TableModel,
    name="audio_chunks",
    base=AudioFiles,
    iterator=pxtf.audio.audio_splitter(AudioFiles.audio, duration=30.0),
):
    pass


@pxt.query
def search_documents(query_text: str, limit: int = 10) -> pxt.Query:
    """Semantic search over document chunks."""
    sim = DocChunks.text.similarity(string=query_text)
    return DocChunks.order_by(sim, asc=False).limit(limit).select(text=DocChunks.text, score=sim, page=DocChunks.page)


@pxt.query
def list_images() -> pxt.Query:
    """List all processed images with metadata."""
    return Images.select(
        uuid=Images.uuid,
        source_url=Images.source_url,
        width=Images.width,
        height=Images.height,
        mode=Images.mode,
        timestamp=Images.timestamp,
    ).order_by(Images.timestamp, asc=False)


@pxt.query
def list_documents() -> pxt.Query:
    """List all documents."""
    return Documents.select(
        uuid=Documents.uuid,
        title=Documents.title,
        document=Documents.document,
        timestamp=Documents.timestamp,
    ).order_by(Documents.timestamp, asc=False)


api = FastAPIRouter(name="pipeline", prefix="/api")
api.add_query_route(path="/search", query=search_documents, method="post")
api.add_insert_route(
    Images,
    path="/ingest/image",
    uploadfile_inputs=["image"],
    inputs=[Images.source_url],
    outputs=[Images.uuid],
)
api.add_insert_route(
    Documents,
    path="/ingest/document",
    uploadfile_inputs=["document"],
    inputs=[Documents.title],
    outputs=[Documents.uuid],
)
api.add_insert_route(
    AudioFiles,
    path="/ingest/audio",
    uploadfile_inputs=["audio"],
    inputs=[AudioFiles.title],
    outputs=[AudioFiles.uuid],
)
