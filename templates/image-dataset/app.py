"""ML dataset application file.

Import images, auto-annotate with DETR, search with CLIP, export.

    pxt schema update app.py datalab
    pxt service update app.py datalab
"""

# ruff: noqa: F821

from __future__ import annotations

import pixeltable as pxt
import pixeltable.functions as pxtf
from pixeltable.functions.huggingface import clip, detr_for_object_detection
from pixeltable.serving import FastAPIRouter

TableModel = pxt.model_base()
clip_embed = clip.using(model_id="openai/clip-vit-base-patch32")


class Dataset(TableModel, name="dataset"):
    uuid = pxt.Column(value=pxtf.uuid.uuid7(), primary_key=True)
    image: pxt.Image
    label: pxt.String | None
    split: pxt.String | None
    source: pxt.String | None
    timestamp: pxt.Timestamp | None
    detections = detr_for_object_detection(image, model_id="facebook/detr-resnet-50", threshold=0.8)
    detection_labels = detections.label_text
    clip_embedding = clip_embed(image)
    __indexes__ = [
        pxt.EmbeddingIndex(image, embedding=clip_embed, name="image_clip_idx"),
    ]


@pxt.query
def search_similar(query_text: str, limit: int = 10) -> pxt.Query:
    """Find images matching a text description via CLIP similarity."""
    sim = Dataset.image.similarity(string=query_text)
    return (
        Dataset.order_by(sim, asc=False)
        .limit(limit)
        .select(Dataset.uuid, Dataset.image, Dataset.label, Dataset.split, score=sim)
    )


def find_similar_images(image_uuid: str, limit: int = 10):
    """Find visually similar images for deduplication and curation.

    Not a @pxt.query because it needs to .collect() an intermediate result
    to fetch the reference image before running similarity search.
    """
    ref = Dataset.where(Dataset.uuid == image_uuid).select(Dataset.image).collect()
    if len(ref) == 0:
        return []
    ref_img = ref["image"][0]
    sim = Dataset.image.similarity(image=ref_img)
    return (
        Dataset.order_by(sim, asc=False)
        .limit(limit)
        .select(Dataset.uuid, Dataset.image, Dataset.label, Dataset.split, score=sim)
        .collect()
        .to_pandas()
        .to_dict("records")
    )


@pxt.query
def list_by_label(label: str) -> pxt.Query:
    """List all images with a given label."""
    return Dataset.where(Dataset.label == label).select(
        Dataset.uuid, Dataset.image, Dataset.label, Dataset.split, Dataset.source
    )


@pxt.query
def dataset_stats() -> pxt.Query:
    """Count per label and split."""
    return Dataset.group_by(Dataset.label, Dataset.split).select(
        Dataset.label, Dataset.split, count=Dataset.uuid.count()
    )


@pxt.query
def get_annotations(limit: int = 50) -> pxt.Query:
    """Get images with their auto-generated annotations."""
    return Dataset.limit(limit).select(
        Dataset.uuid,
        Dataset.image,
        Dataset.label,
        Dataset.split,
        Dataset.detections,
        Dataset.detection_labels,
    )


api = FastAPIRouter(name="datalab", prefix="/api")
api.add_query_route(path="/search", query=search_similar, method="post")
api.add_insert_route(
    Dataset,
    path="/ingest",
    uploadfile_inputs=["image"],
    inputs=[Dataset.label, Dataset.split, Dataset.source],
    outputs=[Dataset.uuid],
)
api.add_query_route(path="/annotations", query=get_annotations, method="get")
api.add_query_route(path="/stats", query=dataset_stats, method="get")
