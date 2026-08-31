"""Video frames at 1 FPS, CLIP index, visual search.

pxt schema update app.py videointel
pxt service update app.py videointel
"""

# ruff: noqa: F821

from __future__ import annotations

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


api = FastAPIRouter(name="videointel", prefix="/api")
api.add_insert_route(
    Videos,
    path="/ingest",
    uploadfile_inputs=["video"],
    inputs=[Videos.title],
    outputs=[Videos.uuid],
    background=True,
)
api.add_query_route(path="/search/visual", query=search_visual, method="post")
