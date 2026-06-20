"""Tests for conditional schema strategies.

Validates register_column(), mixin patterns, and the interaction between
conditional features and create_all() materialization.
"""

import pytest
from collections import OrderedDict
from unittest.mock import MagicMock, patch

from pxt_declarative import (
    Column,
    EmbeddingIndex,
    Model,
    ViewModel,
    _CrossTableColumnRef,
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
# Strategy 1: register_column (post-class mutation)
# ---------------------------------------------------------------------------

class TestRegisterColumnStrategy:
    """register_column is the primary escape hatch for env-gated features."""

    def test_basic_register(self):
        class MyTable(Model):
            __tablename__ = "cond.basic"
            text: str

        MyTable.register_column("summary", Column.text)
        assert "summary" in MyTable._pxt_registered_columns
        assert isinstance(MyTable._pxt_registered_columns["summary"], type(Column.text))

    def test_register_preserves_order(self):
        class MyTable(Model):
            __tablename__ = "cond.order"
            text: str

        MyTable.register_column("first", "expr1")
        MyTable.register_column("second", "expr2")
        MyTable.register_column("third", "expr3")

        keys = list(MyTable._pxt_registered_columns.keys())
        assert keys == ["first", "second", "third"]

    def test_registered_columns_visible_via_cross_ref(self):
        class MyTable(Model):
            __tablename__ = "cond.xref"
            text: str

        MyTable.register_column("summary", "some_expr")
        ref = MyTable.summary
        assert isinstance(ref, _CrossTableColumnRef)
        assert ref.attr_name == "summary"

    def test_registered_column_chains(self):
        """register_column output should support attribute chaining for downstream views."""
        class AudioChunks(ViewModel):
            __tablename__ = "cond.chunks"
            __base__ = "some_iterator"

        AudioChunks.register_column("transcription", "whisper(...)")
        ref = AudioChunks.transcription.text
        assert isinstance(ref, _CrossTableColumnRef)
        assert ref.chain == [("attr", "text")]

    def test_conditional_gating_pattern(self):
        """Simulates the real HAS_OPENAI pattern."""
        class AudioSegments(ViewModel):
            __tablename__ = "cond.segments"
            __base__ = "audio_splitter(...)"

        HAS_OPENAI = True  # simulated
        if HAS_OPENAI:
            AudioSegments.register_column("transcription", "openai.transcriptions(...)")
            AudioSegments.register_column("transcript_text", Column.transcription.text)

        assert "transcription" in AudioSegments._pxt_registered_columns
        assert "transcript_text" in AudioSegments._pxt_registered_columns

    def test_conditional_gating_disabled(self):
        """When the env var is absent, no columns are registered."""
        class AudioSegments(ViewModel):
            __tablename__ = "cond.segments2"
            __base__ = "audio_splitter(...)"

        HAS_OPENAI = False
        if HAS_OPENAI:
            AudioSegments.register_column("transcription", "openai.transcriptions(...)")

        assert "transcription" not in AudioSegments._pxt_registered_columns

    def test_try_except_pattern(self):
        """Simulates the try/except for optional deps like DETR."""
        class Frames(ViewModel):
            __tablename__ = "cond.frames"
            __base__ = "frame_iterator(...)"

        try:
            Frames.register_column("detections", "detr_for_object_detection(...)")
        except Exception:
            pass

        assert "detections" in Frames._pxt_registered_columns

    def test_register_with_embedding_index(self):
        """Conditional columns should work with __indexes__ declared in-class."""
        class Sentences(ViewModel):
            __tablename__ = "cond.sentences"
            __base__ = "string_splitter(...)"
            __indexes__ = [
                EmbeddingIndex(Column.text, idx_name="text_idx", string_embed="embed_fn")
            ]

        assert len(Sentences._pxt_indexes) == 1

    def test_register_index_post_class(self):
        """Indexes added after class creation via register."""
        class MyTable(Model):
            __tablename__ = "cond.post_idx"
            text: str

        MyTable._pxt_indexes.append(
            EmbeddingIndex(Column.text, idx_name="dynamic_idx", string_embed="embed_fn")
        )
        assert len(MyTable._pxt_indexes) == 1

    def test_materialization_includes_registered_columns(self):
        """create_all should materialize both class-defined and registered columns."""
        class MyTable(Model):
            __tablename__ = "cond_mat.table"
            text: str

        MyTable.register_column("derived", Column.text)

        mock_pxt = MagicMock()
        mock_table = MagicMock()
        mock_table.text = "resolved_text"
        mock_pxt.create_table.return_value = mock_table

        with patch.dict("sys.modules", {"pixeltable": mock_pxt}):
            create_all("cond_mat")

        mock_table.add_computed_column.assert_called_once_with(
            derived="resolved_text", if_exists="ignore"
        )


# ---------------------------------------------------------------------------
# Strategy 2: Mixin classes
# ---------------------------------------------------------------------------

class TestMixinStrategy:
    """Mixins allow conditional column sets to be toggled as base classes."""

    def test_mixin_adds_computed_columns(self):
        class TranscriptionMixin:
            transcription = "whisper(...)"

        class AudioChunks(ViewModel, TranscriptionMixin):
            __tablename__ = "mixin.chunks"
            __base__ = "audio_splitter(...)"

        assert "transcription" in AudioChunks._pxt_computed_columns

    def test_conditional_mixin(self):
        """Mixin is only applied when feature is available."""
        class TranscriptionMixin:
            transcription = "whisper(...)"
            transcript_text = Column.transcription.text

        HAS_OPENAI = True

        bases = (ViewModel, TranscriptionMixin) if HAS_OPENAI else (ViewModel,)

        AudioChunks = type("AudioChunks", bases, {
            "__tablename__": "mixin.cond_chunks",
            "__base__": "audio_splitter(...)",
            "__annotations__": {},
        })

        assert "transcription" in AudioChunks._pxt_computed_columns

    def test_mixin_disabled(self):
        class TranscriptionMixin:
            transcription = "whisper(...)"

        HAS_OPENAI = False

        bases = (ViewModel, TranscriptionMixin) if HAS_OPENAI else (ViewModel,)

        AudioChunks = type("AudioChunks", bases, {
            "__tablename__": "mixin.no_chunks",
            "__base__": "audio_splitter(...)",
            "__annotations__": {},
        })

        assert "transcription" not in AudioChunks._pxt_computed_columns

    def test_mixin_combined_with_class_body(self):
        """Class body columns and mixin columns coexist."""
        class DetectionMixin:
            detections = "detr(...)"

        class Frames(ViewModel, DetectionMixin):
            __tablename__ = "mixin.frames"
            __base__ = "frame_iterator(...)"
            thumbnail = "b64_encode(thumbnail(...))"

        assert "thumbnail" in Frames._pxt_computed_columns
        assert "detections" in Frames._pxt_computed_columns


# ---------------------------------------------------------------------------
# Strategy 3: Conditional views (entire ViewModel gated)
# ---------------------------------------------------------------------------

class TestConditionalViews:
    """When an entire view is conditional on an env var."""

    def test_conditional_view_registration(self):
        class Videos(Model):
            __tablename__ = "condview.videos"
            video: str

        HAS_OPENAI = True
        if HAS_OPENAI:
            class TranscriptSentences(ViewModel):
                __tablename__ = "condview.sentences"
                __base__ = "string_splitter(...)"

        models = list_models("condview")
        assert "condview.videos" in models
        assert "condview.sentences" in models

    def test_conditional_view_not_registered(self):
        class Videos(Model):
            __tablename__ = "condview2.videos"
            video: str

        HAS_OPENAI = False
        if HAS_OPENAI:
            class TranscriptSentences(ViewModel):
                __tablename__ = "condview2.sentences"
                __base__ = "string_splitter(...)"

        models = list_models("condview2")
        assert "condview2.videos" in models
        assert "condview2.sentences" not in models


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_register_column_overrides_previous(self):
        """Registering same name twice overwrites."""
        class MyTable(Model):
            __tablename__ = "edge.override"
            col: str

        MyTable.register_column("extra", "expr1")
        MyTable.register_column("extra", "expr2")
        assert MyTable._pxt_registered_columns["extra"] == "expr2"

    def test_register_column_after_create_all(self):
        """Columns registered after create_all are NOT materialized."""
        class MyTable(Model):
            __tablename__ = "edge.late"
            col: str

        mock_pxt = MagicMock()
        mock_table = MagicMock()
        mock_pxt.create_table.return_value = mock_table

        with patch.dict("sys.modules", {"pixeltable": mock_pxt}):
            create_all("edge")

        MyTable.register_column("late_col", "expr")
        # late_col exists in the registry but was not materialized
        assert "late_col" in MyTable._pxt_registered_columns
        assert mock_table.add_computed_column.call_count == 0

    def test_multiple_register_calls_ordered(self):
        """Chained register_column calls maintain insertion order."""
        class MyTable(Model):
            __tablename__ = "edge.multi"
            col: str

        for i in range(10):
            MyTable.register_column(f"col_{i}", f"expr_{i}")

        keys = list(MyTable._pxt_registered_columns.keys())
        assert keys == [f"col_{i}" for i in range(10)]


# ---------------------------------------------------------------------------
# Real-world pattern: knowledge-base conditional transcription
# ---------------------------------------------------------------------------

class TestKnowledgeBasePattern:
    """Simulates the knowledge-base/schema.py conditional OpenAI pattern."""

    def test_full_conditional_pattern(self):
        class Videos(Model):
            __tablename__ = "kbtest.videos"
            video: str

        Videos.register_column("audio_track", "extract_audio(Column.video)")

        class VideoAudioSegments(ViewModel):
            __tablename__ = "kbtest.video_audio_segments"
            __base__ = "audio_splitter(Videos.audio_track, ...)"

        HAS_OPENAI = True

        if HAS_OPENAI:
            VideoAudioSegments.register_column(
                "transcription", "openai.transcriptions(...)"
            )
            VideoAudioSegments.register_column(
                "transcript_text", Column.transcription.text
            )

            class TranscriptSentences(ViewModel):
                __tablename__ = "kbtest.transcript_sentences"
                __parent__ = VideoAudioSegments
                __filter__ = Column.transcription != None
                __iterator__ = "string_splitter(...)"
                __indexes__ = [
                    EmbeddingIndex(
                        Column.text,
                        idx_name="video_transcript_idx",
                        string_embed="text_embed",
                        metric="cosine",
                    )
                ]

        models = list_models("kbtest")
        assert "kbtest.videos" in models
        assert "kbtest.video_audio_segments" in models
        assert "kbtest.transcript_sentences" in models

        # Verify dependency ordering
        plan = create_all("kbtest", dry_run=True)
        order = plan["order"]
        assert order.index("kbtest.videos") < order.index("kbtest.video_audio_segments")
        assert order.index("kbtest.video_audio_segments") < order.index("kbtest.transcript_sentences")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
