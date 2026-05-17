"""Enterprise media processing pipeline -- ingest, process, search across modalities."""

import pixeltable as pxt
from pixeltable.functions import image as pxt_image
from pixeltable.functions.document import document_splitter
from pixeltable.functions.audio import audio_splitter
from pixeltable.functions.huggingface import sentence_transformer
from pixeltable.functions.uuid import uuid7

NAMESPACE = 'pipeline'
EMBED_MODEL = 'all-MiniLM-L6-v2'
embed_fn = sentence_transformer.using(model_id=EMBED_MODEL)

pxt.create_dir(NAMESPACE, if_exists='ignore')

# ---------------------------------------------------------------------------
# Media ingest table -- central registry of all incoming media
# ---------------------------------------------------------------------------
media = pxt.create_table(
    f'{NAMESPACE}.media',
    {
        'url': pxt.String,
        'media_type': pxt.String,  # 'image' | 'document' | 'audio' | 'video'
        'tags': pxt.Json,
        'uuid': uuid7(),
        'timestamp': pxt.Timestamp,
    },
    primary_key=['uuid'],
    if_exists='ignore',
)

# ---------------------------------------------------------------------------
# Image processing
# ---------------------------------------------------------------------------
images = pxt.create_table(
    f'{NAMESPACE}.images',
    {
        'image': pxt.Image,
        'source_url': pxt.String,
        'uuid': uuid7(),
        'timestamp': pxt.Timestamp,
    },
    primary_key=['uuid'],
    if_exists='ignore',
)

images.add_computed_column(
    thumbnail=pxt_image.b64_encode(pxt_image.thumbnail(images.image, size=(320, 320))),
    if_exists='ignore',
)
images.add_computed_column(width=images.image.width, if_exists='ignore')
images.add_computed_column(height=images.image.height, if_exists='ignore')
images.add_computed_column(mode=images.image.mode, if_exists='ignore')

# Optional: CLIP embedding for visual search (uncomment to enable)
# from pixeltable.functions.huggingface import clip
# clip_fn = clip.using(model_id='openai/clip-vit-base-patch32')
# images.add_embedding_index('image', embedding=clip_fn, if_not_exists=True)

# Optional: vision LLM caption (uncomment + set OPENAI_API_KEY)
# from pixeltable.functions.openai import chat_completions
# images.add_computed_column(
#     caption=chat_completions(
#         messages=[{'role': 'user', 'content': [
#             {'type': 'text', 'text': 'Describe this image in one sentence.'},
#             {'type': 'image_url', 'image_url': {'url': images.image}},
#         ]}],
#         model='gpt-4o-mini',
#     ).choices[0].message.content,
#     if_exists='ignore',
# )

# Cloud storage: persist thumbnails to S3
# images.add_computed_column(thumbnail=..., destination='s3://bucket/thumbnails/')

# ---------------------------------------------------------------------------
# Document processing
# ---------------------------------------------------------------------------
documents = pxt.create_table(
    f'{NAMESPACE}.documents',
    {
        'document': pxt.Document,
        'title': pxt.String,
        'uuid': uuid7(),
        'timestamp': pxt.Timestamp,
    },
    primary_key=['uuid'],
    if_exists='ignore',
)

doc_chunks = pxt.create_view(
    f'{NAMESPACE}.doc_chunks',
    documents,
    iterator=document_splitter(
        documents.document,
        separators='sentence,token_limit',
        limit=300,
        metadata='page',
    ),
    if_exists='ignore',
)

doc_chunks.add_embedding_index('text', embedding=embed_fn, if_not_exists=True)

# Optional: LLM summary per document (uncomment + set OPENAI_API_KEY)
# documents.add_computed_column(
#     summary=chat_completions(
#         messages=[{'role': 'user', 'content': 'Summarize:\n' + documents.title}],
#         model='gpt-4o-mini',
#     ).choices[0].message.content,
#     if_exists='ignore',
# )

# ---------------------------------------------------------------------------
# Audio processing
# ---------------------------------------------------------------------------
audio_files = pxt.create_table(
    f'{NAMESPACE}.audio_files',
    {
        'audio': pxt.Audio,
        'title': pxt.String,
        'uuid': uuid7(),
        'timestamp': pxt.Timestamp,
    },
    primary_key=['uuid'],
    if_exists='ignore',
)

audio_chunks = pxt.create_view(
    f'{NAMESPACE}.audio_chunks',
    audio_files,
    iterator=audio_splitter(audio_files.audio, duration=30.0),
    if_exists='ignore',
)

# Optional: transcription (uncomment + install whisper or set OPENAI_API_KEY)
# from pixeltable.functions.openai import transcriptions
# audio_chunks.add_computed_column(
#     transcript=transcriptions(audio=audio_chunks.audio_segment, model='whisper-1'),
#     if_exists='ignore',
# )

# Version control: snapshot before destructive changes
# pxt.create_snapshot('pipeline.snapshot_v1', media, if_exists='ignore')


# ---------------------------------------------------------------------------
# Query functions -- used by pxt serve and pipeline.py
# ---------------------------------------------------------------------------
@pxt.query
def search_documents(query_text: str, limit: int = 10):
    """Semantic search over document chunks."""
    sim = doc_chunks.text.similarity(string=query_text)
    return doc_chunks.order_by(sim, asc=False).limit(limit).select(
        text=doc_chunks.text, score=sim, page=doc_chunks.page
    )


@pxt.query
def list_images():
    """List all processed images with metadata."""
    return images.select(
        uuid=images.uuid,
        source_url=images.source_url,
        width=images.width,
        height=images.height,
        mode=images.mode,
        timestamp=images.timestamp,
    ).order_by(images.timestamp, asc=False)


@pxt.query
def list_documents():
    """List all documents."""
    return documents.select(
        uuid=documents.uuid,
        title=documents.title,
        document=documents.document,
        timestamp=documents.timestamp,
    ).order_by(documents.timestamp, asc=False)

