"""Pixeltable schema for declarative serving.

Defines tables, views, embedding indexes, and @pxt.query functions.
Imported by pxt serve via the `modules` field in pyproject.toml.

    python schema.py                # initialize schema directly
    pxt serve pipeline              # imported automatically via modules = ["schema"]
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
                messages=[
                    {
                        "role": "user",
                        "content": "Summarize in one sentence: " + documents.body,
                    }
                ],
                model="gpt-4o-mini",
            )
            .choices[0]
            .message.content,
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

# ── Query functions ──────────────────────────────────────────────────────────
# Referenced by pxt serve (pixeltable.toml) via dotted path.


@pxt.query
def search_documents(query_text: str, limit: int = 10):
    """Semantic search over document sentences."""
    sim = sentences.text.similarity(string=query_text)
    return (
        sentences.where(sim > 0.3)
        .order_by(sim, asc=False)
        .select(sentences.text, title=sentences.title, sim=sim)
        .limit(limit)
    )


@pxt.query
def list_documents():
    """List all documents."""
    return documents.select(
        documents.uuid,
        documents.title,
        documents.source_id,
        documents.timestamp,
    ).order_by(documents.timestamp, asc=False)


@pxt.query
def list_images():
    """List all images with metadata."""
    return images.select(
        images.uuid,
        images.label,
        images.source_id,
        images.width,
        images.height,
        images.thumbnail,
    ).order_by(images.timestamp, asc=False)


if __name__ == "__main__":
    print("Schema initialized.")
