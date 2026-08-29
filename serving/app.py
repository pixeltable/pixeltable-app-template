"""Application file for declarative serving.

Tables, views, indexes, query functions, and HTTP routes live in this file.

    pxt schema update app.py pipeline
    pxt service update app.py pipeline
    pxt service run app.py pipeline          # foreground, port 8000
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


class Documents(TableModel, name="documents"):
    title: pxt.String
    body: pxt.String
    source_id: pxt.String
    uuid = pxt.Column(value=pxtf.uuid.uuid7(), primary_key=True)
    timestamp: pxt.Timestamp | None


class Sentences(
    TableModel,
    name="sentences",
    base=Documents,
    iterator=pxtf.string.string_splitter(Documents.body, separators="sentence"),
):
    __indexes__ = [
        pxt.EmbeddingIndex(text, embedding=embed_fn, name="sentences_embed"),
    ]


class Images(TableModel, name="images"):
    image: pxt.Image
    label: pxt.String | None
    source_id: pxt.String
    uuid = pxt.Column(value=pxtf.uuid.uuid7(), primary_key=True)
    timestamp: pxt.Timestamp | None
    thumbnail = pxt_image.b64_encode(pxt_image.thumbnail(image, size=(128, 128)))
    width = image.width
    height = image.height
    mode = image.mode


@pxt.query
def search_documents(query_text: str, limit: int = 10) -> pxt.Query:
    """Semantic search over document sentences."""
    sim = Sentences.text.similarity(string=query_text)
    return (
        Sentences.where(sim > 0.3)
        .order_by(sim, asc=False)
        .select(Sentences.text, title=Sentences.title, score=sim)
        .limit(limit)
    )


@pxt.query
def list_documents() -> pxt.Query:
    """List all documents."""
    return Documents.select(
        Documents.uuid,
        Documents.title,
        Documents.source_id,
        Documents.timestamp,
    ).order_by(Documents.timestamp, asc=False)


@pxt.query
def list_images() -> pxt.Query:
    """List all images with metadata."""
    return Images.select(
        Images.uuid,
        Images.label,
        Images.source_id,
        Images.width,
        Images.height,
        Images.thumbnail,
    ).order_by(Images.timestamp, asc=False)


api = FastAPIRouter(name="pipeline", prefix="/api")
api.add_insert_route(
    Documents,
    path="/ingest/document",
    inputs=[Documents.title, Documents.body, Documents.source_id],
    outputs=[Documents.uuid],
)
api.add_insert_route(
    Images,
    path="/ingest/image",
    uploadfile_inputs=["image"],
    inputs=[Images.label, Images.source_id],
    outputs=[Images.uuid],
)
api.add_query_route(path="/search", query=search_documents, method="post")
api.add_query_route(path="/documents", query=list_documents, method="get")
api.add_query_route(path="/images", query=list_images, method="get")
api.add_delete_route(Documents, path="/delete/document")
api.add_delete_route(Images, path="/delete/image")
