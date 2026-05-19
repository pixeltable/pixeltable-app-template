"""Data Lab -- ML dataset engineering pipeline with auto-annotation and embedding search."""

import os

import pixeltable as pxt
from pixeltable.functions.huggingface import clip, detr_for_object_detection
from pixeltable.functions.uuid import uuid7

# ---------------------------------------------------------------------------
# Namespace
# ---------------------------------------------------------------------------

pxt.create_dir('datalab', if_exists='ignore')

# ---------------------------------------------------------------------------
# Dataset table
# ---------------------------------------------------------------------------

dataset = pxt.create_table(
    'datalab.dataset',
    {
        'uuid': uuid7(),
        'image': pxt.Image,
        'label': pxt.String,
        'split': pxt.String,
        'source': pxt.String,
        'timestamp': pxt.Timestamp,
    },
    primary_key=['uuid'],
    if_exists='ignore',
)

dataset = pxt.get_table('datalab.dataset')

# ---------------------------------------------------------------------------
# Auto-annotation: DETR object detection
# ---------------------------------------------------------------------------

try:
    dataset.add_computed_column(
        detections=detr_for_object_detection(
            dataset.image, model_id='facebook/detr-resnet-50', threshold=0.8
        ),
        if_exists='ignore',
    )
    dataset.add_computed_column(
        detection_labels=dataset.detections.label_text,
        if_exists='ignore',
    )
except Exception:
    pass

# ---------------------------------------------------------------------------
# Optional: Vision LLM annotation (requires OPENAI_API_KEY)
# ---------------------------------------------------------------------------

if os.environ.get('OPENAI_API_KEY'):
    try:
        from pixeltable.functions.openai import chat_completions

        dataset.add_computed_column(
            vision_annotation=chat_completions(
                model='gpt-4o-mini',
                messages=[
                    {
                        'role': 'user',
                        'content': [
                            {
                                'type': 'image_url',
                                'image_url': {'url': dataset.image},
                            },
                            {
                                'type': 'text',
                                'text': (
                                    'Classify this image into exactly one category. '
                                    'Return ONLY the category name, no explanation.'
                                ),
                            },
                        ],
                    }
                ],
            ).choices[0].message.content,
            if_exists='ignore',
        )
    except Exception:
        pass

# ---------------------------------------------------------------------------
# CLIP embeddings for visual similarity search
# ---------------------------------------------------------------------------

clip_embed = clip.using(model_id='openai/clip-vit-base-patch32')

dataset.add_computed_column(
    clip_embedding=clip_embed(dataset.image),
    if_exists='ignore',
)

dataset.add_embedding_index(
    'image',
    idx_name='image_clip_idx',
    embedding=clip_embed,
    if_exists='ignore',
)

# ---------------------------------------------------------------------------
# Query functions
# ---------------------------------------------------------------------------


@pxt.query
def search_similar(query_text: str, limit: int = 10):
    """Find images matching a text description via CLIP similarity."""
    sim = dataset.image.similarity(string=query_text)
    return dataset.order_by(sim, asc=False).limit(limit).select(
        dataset.uuid, dataset.image, dataset.label, dataset.split, sim
    )


def find_similar_images(image_uuid: str, limit: int = 10):
    """Find visually similar images for deduplication and curation.

    Not a @pxt.query because it needs to .collect() an intermediate result
    to fetch the reference image before running similarity search.
    """
    ref = dataset.where(dataset.uuid == image_uuid).select(dataset.image).collect()
    if len(ref) == 0:
        return []
    ref_img = ref['image'][0]
    sim = dataset.image.similarity(image=ref_img)
    return (
        dataset.order_by(sim, asc=False)
        .limit(limit)
        .select(dataset.uuid, dataset.image, dataset.label, dataset.split, sim)
        .collect()
        .to_pandas()
        .to_dict('records')
    )


@pxt.query
def list_by_label(label: str):
    """List all images with a given label."""
    return dataset.where(dataset.label == label).select(
        dataset.uuid, dataset.image, dataset.label, dataset.split, dataset.source
    )


@pxt.query
def dataset_stats():
    """Count per label and split."""
    return dataset.group_by(dataset.label, dataset.split).select(
        dataset.label, dataset.split, count=dataset.uuid.count()
    )


@pxt.query
def get_annotations(limit: int = 50):
    """Get images with their auto-generated annotations."""
    cols = [dataset.uuid, dataset.image, dataset.label, dataset.split]
    if hasattr(dataset, 'detections'):
        cols.append(dataset.detections)
    if hasattr(dataset, 'detection_labels'):
        cols.append(dataset.detection_labels)
    return dataset.limit(limit).select(*cols)
