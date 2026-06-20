"""Tests for create_all() -- topological sort, materialization, and edge cases.

Validates:
- Correct ordering for all dependency patterns
- Namespace filtering
- Directory creation
- Circular dependency detection
- checkfirst behavior
- Deep cross-table reference resolution
- The full materialization pipeline against mocked Pixeltable
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
    _topological_sort,
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
# Topological sort correctness
# ---------------------------------------------------------------------------

class TestTopologicalSort:
    def test_single_table(self):
        class T(Model):
            __tablename__ = "ts.single"
            col: str

        result = create_all("ts", dry_run=True)
        assert result["order"] == ["ts.single"]

    def test_linear_chain(self):
        class A(Model):
            __tablename__ = "ts2.a"
            col: str

        class B(ViewModel):
            __tablename__ = "ts2.b"
            __base__ = ("iter", A.col)

        B.register_column("derived", "expr")

        class C(ViewModel):
            __tablename__ = "ts2.c"
            __base__ = ("iter", B.derived)

        result = create_all("ts2", dry_run=True)
        assert result["order"] == ["ts2.a", "ts2.b", "ts2.c"]

    def test_diamond_dependency(self):
        """A -> B, A -> C, B -> D, C -> D"""
        class A(Model):
            __tablename__ = "ts3.a"
            col: str

        class B(ViewModel):
            __tablename__ = "ts3.b"
            __base__ = ("iter1", A.col)

        class C(ViewModel):
            __tablename__ = "ts3.c"
            __base__ = ("iter2", A.col)

        B.register_column("b_col", "expr")
        C.register_column("c_col", "expr")

        class D(ViewModel):
            __tablename__ = "ts3.d"
            __base__ = ("merge", B.b_col, C.c_col)

        result = create_all("ts3", dry_run=True)
        order = result["order"]
        assert order[0] == "ts3.a"
        assert order.index("ts3.b") < order.index("ts3.d")
        assert order.index("ts3.c") < order.index("ts3.d")

    def test_multiple_independent_tables(self):
        class Docs(Model):
            __tablename__ = "ts4.docs"
            doc: str

        class Images(Model):
            __tablename__ = "ts4.images"
            image: str

        class Videos(Model):
            __tablename__ = "ts4.videos"
            video: str

        result = create_all("ts4", dry_run=True)
        assert len(result["order"]) == 3

    def test_wide_fan_out(self):
        """One parent -> 5 views."""
        class Parent(Model):
            __tablename__ = "ts5.parent"
            data: str

        views = []
        for i in range(5):
            v = type(f"View{i}", (ViewModel,), {
                "__tablename__": f"ts5.view_{i}",
                "__base__": ("iter", Parent.data),
                "__annotations__": {},
            })
            views.append(v)

        result = create_all("ts5", dry_run=True)
        order = result["order"]
        assert order[0] == "ts5.parent"
        assert len(order) == 6

    def test_circular_dependency_detected(self):
        """Should raise ValueError on circular deps."""
        class A(Model):
            __tablename__ = "circ.a"
            col: str

        class B(ViewModel):
            __tablename__ = "circ.b"
            __base__ = ("iter", A.col)

        # Manually inject a circular dependency
        B.register_column("b_out", "expr")
        A._pxt_computed_columns["a_from_b"] = B.b_out

        with pytest.raises(ValueError, match="[Cc]ircular"):
            create_all("circ", dry_run=True)

        # Clean up to avoid polluting other tests
        del A._pxt_computed_columns["a_from_b"]


# ---------------------------------------------------------------------------
# Namespace filtering
# ---------------------------------------------------------------------------

class TestNamespaceFiltering:
    def test_only_matching_namespace(self):
        class A(Model):
            __tablename__ = "ns_a.table1"
            col: str

        class B(Model):
            __tablename__ = "ns_b.table2"
            col: str

        result = create_all("ns_a", dry_run=True)
        assert result["order"] == ["ns_a.table1"]

    def test_none_namespace_includes_all(self):
        class A(Model):
            __tablename__ = "all1.table1"
            col: str

        class B(Model):
            __tablename__ = "all2.table2"
            col: str

        result = create_all(dry_run=True)
        assert "all1.table1" in result["order"]
        assert "all2.table2" in result["order"]

    def test_empty_namespace_returns_empty(self):
        class A(Model):
            __tablename__ = "notempty.table1"
            col: str

        result = create_all("nonexistent", dry_run=True)
        assert result["order"] == []


# ---------------------------------------------------------------------------
# Full materialization pipeline (mocked Pixeltable)
# ---------------------------------------------------------------------------

class TestMaterialization:
    def _mock_pxt(self):
        """Create a mock Pixeltable module with table/view factories."""
        mock = MagicMock()
        tables = {}

        def make_table(name, schema, **kwargs):
            t = MagicMock(name=f"Table({name})")
            tables[name] = t
            # Make column access return mock column objects
            for col_name in schema:
                setattr(t, col_name, MagicMock(name=f"{name}.{col_name}"))
            return t

        def make_view(name, parent, iterator=None, **kwargs):
            v = MagicMock(name=f"View({name})")
            tables[name] = v
            return v

        mock.create_table.side_effect = make_table
        mock.create_view.side_effect = make_view
        return mock, tables

    def test_table_creation_order(self):
        class A(Model):
            __tablename__ = "mat.a"
            col: str

        class B(ViewModel):
            __tablename__ = "mat.b"
            __base__ = ("iter", A.col)

        mock_pxt, _ = self._mock_pxt()

        with patch.dict("sys.modules", {"pixeltable": mock_pxt}):
            create_all("mat")

        calls = [c[0][0] for c in mock_pxt.create_table.call_args_list]
        assert calls == ["mat.a"]
        view_calls = [c[0][0] for c in mock_pxt.create_view.call_args_list]
        assert view_calls == ["mat.b"]

    def test_directory_created(self):
        class T(Model):
            __tablename__ = "dirtest.table"
            col: str

        mock_pxt, _ = self._mock_pxt()

        with patch.dict("sys.modules", {"pixeltable": mock_pxt}):
            create_all("dirtest")

        mock_pxt.create_dir.assert_called_once_with("dirtest", if_exists="ignore")

    def test_primary_key_passed(self):
        class T(Model):
            __tablename__ = "pk.table"
            __primary_key__ = ["uuid"]
            uuid: str
            data: str

        mock_pxt, _ = self._mock_pxt()

        with patch.dict("sys.modules", {"pixeltable": mock_pxt}):
            create_all("pk")

        _, kwargs = mock_pxt.create_table.call_args
        assert kwargs["primary_key"] == ["uuid"]

    def test_checkfirst_true(self):
        class T(Model):
            __tablename__ = "cf.table"
            col: str

        mock_pxt, _ = self._mock_pxt()

        with patch.dict("sys.modules", {"pixeltable": mock_pxt}):
            create_all("cf", checkfirst=True)

        _, kwargs = mock_pxt.create_table.call_args
        assert kwargs["if_exists"] == "ignore"

    def test_checkfirst_false(self):
        class T(Model):
            __tablename__ = "cf2.table"
            col: str

        mock_pxt, _ = self._mock_pxt()

        with patch.dict("sys.modules", {"pixeltable": mock_pxt}):
            create_all("cf2", checkfirst=False)

        _, kwargs = mock_pxt.create_table.call_args
        assert kwargs["if_exists"] == "error"

    def test_computed_columns_added_in_order(self):
        class T(Model):
            __tablename__ = "cc.table"
            text: str

        T.register_column("first", Column.text)
        T.register_column("second", Column.first)

        mock_pxt, _ = self._mock_pxt()

        with patch.dict("sys.modules", {"pixeltable": mock_pxt}):
            tables = create_all("cc")

        table = tables["cc.table"]
        add_calls = table.add_computed_column.call_args_list
        assert len(add_calls) == 2
        # First call should have 'first', second should have 'second'
        assert "first" in add_calls[0][1]
        assert "second" in add_calls[1][1]

    def test_embedding_indexes_created(self):
        embed_fn = object()

        class T(Model):
            __tablename__ = "idx.table"
            text: str
            __indexes__ = [
                EmbeddingIndex(Column.text, idx_name="text_idx", string_embed=embed_fn)
            ]

        mock_pxt, _ = self._mock_pxt()

        with patch.dict("sys.modules", {"pixeltable": mock_pxt}):
            tables = create_all("idx")

        table = tables["idx.table"]
        table.add_embedding_index.assert_called_once()
        call_kwargs = table.add_embedding_index.call_args[1]
        assert call_kwargs["idx_name"] == "text_idx"
        assert call_kwargs["string_embed"] is embed_fn

    def test_full_pipeline_video_search(self):
        """Simulate the video-search schema with mocked Pixeltable."""
        class Videos(Model):
            __tablename__ = "full.videos"
            __primary_key__ = ["uuid"]
            video: str
            title: str
            uuid: str

        Videos.register_column("audio", Column.video)

        embed = object()

        class Frames(ViewModel):
            __tablename__ = "full.frames"
            __base__ = ("frame_iterator", Videos.video, 1.0)
            thumbnail = Column.frame
            __indexes__ = [
                EmbeddingIndex(Column.frame, idx_name="frames_idx", embedding=embed)
            ]

        class AudioChunks(ViewModel):
            __tablename__ = "full.audio_chunks"
            __base__ = ("audio_splitter", Videos.audio, 30.0)

        AudioChunks.register_column("transcription", Column.audio_segment)

        class Sentences(ViewModel):
            __tablename__ = "full.sentences"
            __parent__ = AudioChunks
            __filter__ = Column.transcription != None
            __iterator__ = ("string_splitter", AudioChunks.transcription.text)
            __indexes__ = [
                EmbeddingIndex(Column.text, idx_name="text_idx", string_embed=embed)
            ]

        mock_pxt, _ = self._mock_pxt()

        with patch.dict("sys.modules", {"pixeltable": mock_pxt}):
            tables = create_all("full")

        # Verify all 4 entities were created
        assert len(tables) == 4
        assert "full.videos" in tables
        assert "full.frames" in tables
        assert "full.audio_chunks" in tables
        assert "full.sentences" in tables

        # Verify create_table called once, create_view called 3x
        assert mock_pxt.create_table.call_count == 1
        assert mock_pxt.create_view.call_count == 3

    def test_return_value_maps_tablename_to_object(self):
        class T(Model):
            __tablename__ = "ret.table"
            col: str

        mock_pxt, _ = self._mock_pxt()

        with patch.dict("sys.modules", {"pixeltable": mock_pxt}):
            result = create_all("ret")

        assert "ret.table" in result
        assert result["ret.table"] is T._pxt_table


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
