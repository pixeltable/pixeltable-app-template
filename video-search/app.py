"""Video frames at 1 FPS, CLIP index, visual search, and image ingest.

pxt schema update app.py videointel
pxt service update app.py videointel
"""

# ruff: noqa: F821

import pixeltable as pxt
import pixeltable.functions as pxtf
from pixeltable.functions import image as pxt_image
from pixeltable.functions.huggingface import clip
from pixeltable.serving import FastAPIRouter

TableModel = pxt.model_base()
clip_embed = clip.using(model_id="openai/clip-vit-base-patch32")


class Videos(TableModel, name="videos"):
    video: pxt.Video
    title: pxt.String
    uuid = pxt.Column(value=pxtf.uuid.uuid7(), primary_key=True)
    timestamp: pxt.Timestamp | None


class Frames(
    TableModel,
    name="frames",
    base=Videos,
    iterator=pxtf.video.frame_iterator(Videos.video, fps=1.0),
):
    thumbnail = pxt_image.b64_encode(pxt_image.thumbnail(frame, size=(320, 320)))
    __indexes__ = [
        pxt.EmbeddingIndex(frame, embedding=clip_embed, name="frames_clip"),
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
def search_visual(query_text: str, limit: int = 20) -> pxt.Query:
    """CLIP similarity search on video frames."""
    sim = Frames.frame.similarity(string=query_text)
    return (
        Frames.where(sim > 0.2)
        .order_by(sim, asc=False)
        .select(
            Frames.thumbnail,
            timestamp=Frames.frame_attrs.time,
            score=sim,
        )
        .limit(limit)
    )


@pxt.query
def list_images() -> pxt.Query:
    """List ingested images with metadata."""
    return Images.select(
        Images.uuid,
        Images.label,
        Images.source_id,
        Images.width,
        Images.height,
        Images.thumbnail,
    ).order_by(Images.timestamp, asc=False)


api = FastAPIRouter(name="videointel", prefix="/api")
api.add_insert_route(
    Videos,
    path="/ingest",
    uploadfile_inputs=["video"],
    inputs=[Videos.title],
    outputs=[Videos.uuid],
    background=True,
)
api.add_insert_route(
    Images,
    path="/ingest/image",
    uploadfile_inputs=["image"],
    inputs=[Images.label, Images.source_id],
    outputs=[Images.uuid],
)
api.add_query_route(path="/search/visual", query=search_visual, method="post")
api.add_query_route(path="/images", query=list_images, method="get")
api.add_delete_route(Videos, path="/delete/video")
api.add_delete_route(Images, path="/delete/image")
