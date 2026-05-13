"""Pixeltable schema for the orchestration pipeline.

Defines tables, views, embedding indexes, and computed columns.
Idempotent — safe to import or run multiple times.

    python schema.py                # initialize schema directly
    import schema                   # used by pipeline.py
"""
import os

import pixeltable as pxt
from pixeltable.functions import image as pxt_image
from pixeltable.functions.huggingface import sentence_transformer
from pixeltable.functions.string import string_splitter
from pixeltable.functions.uuid import uuid7

pxt.create_dir("pipeline", if_exists="ignore")

embed_fn = sentence_transformer.using(model_id="all-MiniLM-L6-v2")

# ── Documents ────────────────────────────────────────────────────────────────
# Text documents with sentence-level chunking and semantic search.

documents = pxt.create_table(
    "pipeline.documents",
    {
        "title": pxt.String,
        "body": pxt.String,
        "source_id": pxt.String,
        "uuid": uuid7(),
        "timestamp": pxt.Timestamp,
    },
    primary_key=["uuid"],
    if_exists="ignore",
)

sentences = pxt.create_view(
    "pipeline.sentences",
    documents,
    iterator=string_splitter(text=documents.body, separators="sentence"),
    if_exists="ignore",
)
sentences.add_embedding_index(
    "text", idx_name="sentences_embed", string_embed=embed_fn, if_exists="ignore"
)

if os.getenv("OPENAI_API_KEY"):
    try:
        from pixeltable.functions.openai import chat_completions

        documents.add_computed_column(
            summary=chat_completions(
                messages=[{"role": "user", "content": "Summarize in one sentence: " + documents.body}],
                model="gpt-4o-mini",
            ).choices[0].message.content,
            if_exists="ignore",
        )
    except Exception as exc:
        print(f"Skipping summary column: {exc}")

# ── Images ───────────────────────────────────────────────────────────────────
# Images with auto-generated thumbnails and metadata extraction.

images = pxt.create_table(
    "pipeline.images",
    {
        "image": pxt.Image,
        "label": pxt.String,
        "source_id": pxt.String,
        "uuid": uuid7(),
        "timestamp": pxt.Timestamp,
    },
    primary_key=["uuid"],
    if_exists="ignore",
)

images.add_computed_column(
    thumbnail=pxt_image.b64_encode(pxt_image.thumbnail(images.image, size=(128, 128))),
    if_exists="ignore",
)
images.add_computed_column(width=images.image.width, if_exists="ignore")
images.add_computed_column(height=images.image.height, if_exists="ignore")
images.add_computed_column(mode=images.image.mode, if_exists="ignore")

if __name__ == "__main__":
    print("Schema initialized.")
