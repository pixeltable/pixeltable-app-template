"""Custom UDFs for the video-search template."""

import pixeltable as pxt


@pxt.udf
def has_label(labels: list[str] | None, label: str) -> bool:
    """Check whether a specific label appears in a list of detected object labels."""
    return label in (labels or [])
