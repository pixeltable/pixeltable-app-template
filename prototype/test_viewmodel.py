"""Tests for ViewModel patterns.

Covers the three view declaration variants:
1. Iterator-only: __base__ = iterator(ParentModel.column, ...)
2. Filtered parent + iterator: __parent__ + __filter__ + __iterator__
3. Chain API: __base__ = ParentModel.where(condition)  (for simple filtered views)
"""

import pytest
from collections import OrderedDict
from unittest.mock import MagicMock, call, patch

from pxt_declarative import (
    Column,
    EmbeddingIndex,
    Model,
    ViewModel,
    _CrossTableColumnRef,
    _FilterExpr,
    _ViewBase,
    clear_registry,
    create_all,
    list_models,
)


@pytest.fixture(autouse=True)
def clean_registry():
    clear_registry()
    yield
    clear_registry()


# ---------------------------------------------------------------------------
# Pattern 1: Iterator-only views
# ---------------------------------------------------------------------------

class TestIteratorOnlyView:
    """__base__ = iterator(ParentModel.column, ...) -- the most common pattern."""

    def test_base_captures_iterator_expression(self):
        class Videos(Model):
            __tablename__ = "vp1.videos"
            video: str

        class Frames(ViewModel):
            __tablename__ = "vp1.frames"
            __base__ = ("frame_iterator", Videos.video, 1.0)

        assert Frames._pxt_view_base is not None
        assert Frames._pxt_is_view is True

    def test_iterator_view_has_no_stored_columns(self):
        class Videos(Model):
            __tablename__ = "vp1b.videos"
            video: str

        class Frames(ViewModel):
            __tablename__ = "vp1b.frames"
            __base__ = ("frame_iterator", Videos.video, 1.0)

        assert len(Frames._pxt_stored_columns) == 0

    def test_computed_columns_on_iterator_view(self):
        class Videos(Model):
            __tablename__ = "vp1c.videos"
            video: str

        class Frames(ViewModel):
            __tablename__ = "vp1c.frames"
            __base__ = ("frame_iterator", Videos.video, 1.0)
            thumbnail = ("b64_encode", Column.frame)

        assert "thumbnail" in Frames._pxt_computed_columns

    def test_indexes_on_iterator_view(self):
        class Videos(Model):
            __tablename__ = "vp1d.videos"
            video: str

        embed_fn = object()

        class Frames(ViewModel):
            __tablename__ = "vp1d.frames"
            __base__ = ("frame_iterator", Videos.video, 1.0)
            __indexes__ = [
                EmbeddingIndex(Column.frame, idx_name="frame_idx", embedding=embed_fn)
            ]

        assert len(Frames._pxt_indexes) == 1
        assert Frames._pxt_indexes[0].idx_name == "frame_idx"

    def test_dependency_detected_from_base(self):
        class Videos(Model):
            __tablename__ = "vp1e.videos"
            video: str

        class Frames(ViewModel):
            __tablename__ = "vp1e.frames"
            __base__ = ("frame_iterator", Videos.video, 1.0)

        plan = create_all("vp1e", dry_run=True)
        order = plan["order"]
        assert order.index("vp1e.videos") < order.index("vp1e.frames")

    def test_chained_views(self):
        """View -> View chain: videos -> audio_chunks -> sentences."""
        class Videos(Model):
            __tablename__ = "vp1f.videos"
            video: str

        Videos.register_column("audio", "extract_audio(Column.video)")

        class AudioChunks(ViewModel):
            __tablename__ = "vp1f.audio_chunks"
            __base__ = ("audio_splitter", Videos.audio, 30.0)

        AudioChunks.register_column("transcription", "whisper(...)")

        class Sentences(ViewModel):
            __tablename__ = "vp1f.sentences"
            __parent__ = AudioChunks
            __filter__ = Column.transcription != None
            __iterator__ = ("string_splitter", AudioChunks.transcription.text)

        plan = create_all("vp1f", dry_run=True)
        order = plan["order"]
        assert order == ["vp1f.videos", "vp1f.audio_chunks", "vp1f.sentences"]


# ---------------------------------------------------------------------------
# Pattern 2: Filtered parent + iterator
# ---------------------------------------------------------------------------

class TestFilteredViewPattern:
    """__parent__ + __filter__ + __iterator__ -- for views on filtered parents."""

    def test_parent_filter_iterator_attributes(self):
        class AudioChunks(Model):
            __tablename__ = "vp2.chunks"
            transcription: str

        class Sentences(ViewModel):
            __tablename__ = "vp2.sentences"
            __parent__ = AudioChunks
            __filter__ = Column.transcription != None
            __iterator__ = ("string_splitter", AudioChunks.transcription.text)

        assert Sentences._pxt_view_parent is AudioChunks
        assert isinstance(Sentences._pxt_view_filter, _FilterExpr)
        assert Sentences._pxt_view_iterator is not None

    def test_filter_expr_operations(self):
        expr = Column.score > 0.5
        assert isinstance(expr, _FilterExpr)
        assert expr.op == "gt"

    def test_compound_filter(self):
        expr = (Column.score > 0.5) & (Column.text != None)
        assert isinstance(expr, _FilterExpr)
        assert expr.op == "and"

    def test_filtered_view_dependency(self):
        class Parent(Model):
            __tablename__ = "vp2b.parent"
            col: str

        class Filtered(ViewModel):
            __tablename__ = "vp2b.filtered"
            __parent__ = Parent
            __filter__ = Column.col != None
            __iterator__ = ("string_splitter", Parent.col)

        plan = create_all("vp2b", dry_run=True)
        order = plan["order"]
        assert order.index("vp2b.parent") < order.index("vp2b.filtered")

    def test_materialization_with_filter(self):
        """Ensure create_all applies the filter to the parent before creating the view."""
        class Parent(Model):
            __tablename__ = "vp2c.parent"
            status: str

        class Filtered(ViewModel):
            __tablename__ = "vp2c.filtered"
            __parent__ = Parent
            __filter__ = Column.status != None
            __iterator__ = ("split", Parent.status)

        mock_pxt = MagicMock()
        mock_table = MagicMock()
        mock_filtered_table = MagicMock()
        mock_view = MagicMock()

        mock_pxt.create_table.return_value = mock_table
        mock_table.where.return_value = mock_filtered_table
        mock_pxt.create_view.return_value = mock_view
        # Make status resolve to something
        mock_table.status = MagicMock()
        mock_table.status.__ne__ = MagicMock(return_value="filter_expr")

        with patch.dict("sys.modules", {"pixeltable": mock_pxt}):
            tables = create_all("vp2c")

        # Verify .where() was called on the parent table
        mock_table.where.assert_called_once()
        # Verify create_view was called with the filtered result
        mock_pxt.create_view.assert_called_once()
        view_call_args = mock_pxt.create_view.call_args
        assert view_call_args[0][1] == mock_filtered_table


# ---------------------------------------------------------------------------
# Pattern 3: Model.where() chain API
# ---------------------------------------------------------------------------

class TestWhereChainView:
    """__base__ = ParentModel.where(condition) -- for simple filtered views without iterators."""

    def test_where_returns_viewbase(self):
        class Parent(Model):
            __tablename__ = "vp3.parent"
            status: str

        result = Parent.where(Column.status == "active")
        assert isinstance(result, _ViewBase)
        assert result.model_cls is Parent

    def test_viewbase_as_base(self):
        class Parent(Model):
            __tablename__ = "vp3b.parent"
            status: str

        class ActiveOnly(ViewModel):
            __tablename__ = "vp3b.active"
            __base__ = Parent.where(Column.status == "active")

        assert isinstance(ActiveOnly._pxt_view_base, _ViewBase)
        assert ActiveOnly._pxt_view_base.model_cls is Parent

    def test_viewbase_dependency(self):
        class Parent(Model):
            __tablename__ = "vp3c.parent"
            status: str

        class ActiveOnly(ViewModel):
            __tablename__ = "vp3c.active"
            __base__ = Parent.where(Column.status == "active")

        plan = create_all("vp3c", dry_run=True)
        order = plan["order"]
        assert order.index("vp3c.parent") < order.index("vp3c.active")


# ---------------------------------------------------------------------------
# Complex real-world patterns
# ---------------------------------------------------------------------------

class TestRealWorldViewPatterns:
    """Patterns drawn from actual templates."""

    def test_video_pipeline_topology(self):
        """Full video pipeline: videos -> frames, audio_chunks -> sentences."""
        class Videos(Model):
            __tablename__ = "rw.videos"
            video: str

        Videos.register_column("audio", "extract_audio(...)")

        class Frames(ViewModel):
            __tablename__ = "rw.frames"
            __base__ = ("frame_iterator", Videos.video, 1.0)

        class AudioChunks(ViewModel):
            __tablename__ = "rw.audio_chunks"
            __base__ = ("audio_splitter", Videos.audio, 30.0)

        AudioChunks.register_column("transcription", "whisper(...)")

        class Sentences(ViewModel):
            __tablename__ = "rw.sentences"
            __parent__ = AudioChunks
            __filter__ = Column.transcription != None
            __iterator__ = ("string_splitter", AudioChunks.transcription.text)

        plan = create_all("rw", dry_run=True)
        order = plan["order"]

        # Videos must come first
        assert order[0] == "rw.videos"
        # Frames and AudioChunks both depend on Videos (order between them doesn't matter)
        assert "rw.frames" in order
        assert "rw.audio_chunks" in order
        # Sentences must come after AudioChunks
        assert order.index("rw.audio_chunks") < order.index("rw.sentences")

    def test_knowledge_base_multimodal(self):
        """Multiple tables, each with their own views: docs, images, videos, audio."""
        class Documents(Model):
            __tablename__ = "kb2.documents"
            doc: str

        class DocChunks(ViewModel):
            __tablename__ = "kb2.doc_chunks"
            __base__ = ("document_splitter", Documents.doc)
            __indexes__ = [
                EmbeddingIndex(Column.text, idx_name="doc_idx", string_embed="embed")
            ]

        class Images(Model):
            __tablename__ = "kb2.images"
            image: str
            __indexes__ = [
                EmbeddingIndex(Column.image, idx_name="img_idx", embedding="clip")
            ]

        class Videos(Model):
            __tablename__ = "kb2.videos"
            video: str

        class VideoFrames(ViewModel):
            __tablename__ = "kb2.video_frames"
            __base__ = ("frame_iterator", Videos.video, 1.0)

        plan = create_all("kb2", dry_run=True)
        order = plan["order"]

        # Tables before their views
        assert order.index("kb2.documents") < order.index("kb2.doc_chunks")
        assert order.index("kb2.videos") < order.index("kb2.video_frames")
        # Images is standalone -- just needs to exist
        assert "kb2.images" in order

    def test_view_with_computed_and_index(self):
        """View that has both computed columns and embedding indexes."""
        class Parent(Model):
            __tablename__ = "vi.parent"
            video: str

        class Frames(ViewModel):
            __tablename__ = "vi.frames"
            __base__ = ("frame_iterator", Parent.video, 1.0)

            thumbnail = ("thumbnail", Column.frame)
            b64 = ("b64_encode", Column.thumbnail)

            __indexes__ = [
                EmbeddingIndex(Column.frame, idx_name="frame_idx", embedding="clip")
            ]

        assert len(Frames._pxt_computed_columns) == 2
        assert "thumbnail" in Frames._pxt_computed_columns
        assert "b64" in Frames._pxt_computed_columns
        assert len(Frames._pxt_indexes) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
