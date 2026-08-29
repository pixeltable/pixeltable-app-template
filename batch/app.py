"""Application file for the batch pipeline.

Tables, views, and indexes. No HTTP. Apply, then run pipeline.py:

    pxt schema update app.py pipeline
    python pipeline.py
"""

# ruff: noqa: F821

from __future__ import annotations

import pixeltable as pxt
import pixeltable.functions as pxtf
from pixeltable.functions import image as pxt_image
from pixeltable.functions.huggingface import sentence_transformer

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
