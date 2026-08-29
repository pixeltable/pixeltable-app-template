"""Export helpers for ML training formats."""

from pathlib import Path

import pixeltable as pxt
from app import TableModel
from pixeltable.io import export_parquet


def _dataset():
    TableModel.update_all("datalab")
    return pxt.get_table("datalab.dataset")


def export_to_parquet(output_path: str = "exports/dataset.parquet") -> None:
    """Export the full dataset to Parquet format."""
    dataset = _dataset()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    export_parquet(dataset, output_path)
    print(f"Exported to {output_path}")


def export_to_pytorch(split: str = "train", image_format: str = "pt"):
    """Return a PyTorch IterableDataset for the given split.

    Args:
        split: Dataset split to export ('train', 'val', or 'test').
        image_format: 'pt' for CxHxW float32 tensors, 'np' for HxWxC uint8 arrays.

    Returns:
        A torch IterableDataset ready for DataLoader.
    """
    dataset = _dataset()
    query = dataset.where(dataset.split == split).select(dataset.image, dataset.label)
    return query.to_pytorch_dataset(image_format=image_format)


def export_to_coco(output_dir: str = "exports/coco") -> Path:
    """Export object detections in COCO format.

    Requires the `detections` computed column (DETR) to be present.

    Returns:
        Path to the generated COCO JSON file.
    """
    from pixeltable.functions.huggingface import detr_to_coco

    dataset = _dataset()
    query = dataset.select(detr_to_coco(dataset.image, dataset.detections))
    coco_path = query.to_coco_dataset()
    print(f"COCO dataset written to {coco_path}")
    return coco_path


def export_to_pandas(split: str | None = None):
    """Collect dataset rows as a pandas DataFrame.

    Args:
        split: Optional split filter. If None, exports all rows.

    Returns:
        A pandas DataFrame with image paths, labels, and metadata.
    """
    dataset = _dataset()
    query = dataset if split is None else dataset.where(dataset.split == split)
    df = query.select(dataset.uuid, dataset.image, dataset.label, dataset.split, dataset.source).collect().to_pandas()
    print(f"Collected {len(df)} samples")
    return df


if __name__ == "__main__":
    export_to_parquet()
