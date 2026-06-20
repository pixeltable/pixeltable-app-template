"""Tests for the declarative schema layer.

Tests the metaclass, Column sentinel, cross-table refs, topological sort,
and the full create_all() flow against a mock Pixeltable API.
"""

import pytest
from collections import OrderedDict
from unittest.mock import MagicMock, call, patch
from pxt_declarative import (
    Column,
    EmbeddingIndex,
    Model,
    ViewModel,
    _ColumnProxy,
    _CrossTableColumnRef,
    _FilterExpr,
    _MODEL_REGISTRY,
    _ViewBase,
    _topological_sort,
    clear_registry,
    create_all,
    list_models,
)


@pytest.fixture(autouse=True)
def clean_registry():
    """Ensure each test starts with a clean model registry."""
    clear_registry()
    yield
    clear_registry()


# ---------------------------------------------------------------------------
# Column sentinel tests
# ---------------------------------------------------------------------------

class TestColumnSentinel:
    def test_simple_attr(self):
        ref = Column.video
        assert isinstance(ref, _ColumnProxy)
        assert ref._name == "video"
        assert ref._chain == []

    def test_chained_attr(self):
        ref = Column.transcription.text
        assert ref._name == "transcription"
        assert ref._chain == [("attr", "text")]

    def test_deep_chain(self):
        ref = Column.final_response.content[0].text
        assert ref._name == "final_response"
        assert ref._chain == [
            ("attr", "content"),
            ("item", 0),
            ("attr", "text"),
        ]

    def test_repr(self):
        assert repr(Column.video) == "Column.video"
        assert repr(Column.transcription.text) == "Column.transcription.text"
        assert repr(Column.response.content[0].text) == "Column.response.content[0].text"

    def test_comparison_returns_filter(self):
        expr = Column.transcription != None
        assert isinstance(expr, _FilterExpr)
        assert expr.op == "ne"

    def test_mod_operator(self):
        ref = Column.int_col % 2
        assert ref._name == "int_col"
        assert ref._chain == [("mod", 2)]

    def test_resolve_simple(self):
        mock_table = MagicMock()
        mock_table.video = "resolved_video_col"
        ref = Column.video
        assert ref.resolve(mock_table) == "resolved_video_col"

    def test_resolve_chained(self):
        mock_table = MagicMock()
        mock_text = MagicMock()
        mock_table.transcription.text = mock_text
        ref = Column.transcription.text
        assert ref.resolve(mock_table) == mock_text


# ---------------------------------------------------------------------------
# Model metaclass tests
# ---------------------------------------------------------------------------

class TestModelMeta:
    def test_stored_columns(self):
        class MyTable(Model):
            __tablename__ = "test.my_table"
            col_a: str
            col_b: int

        assert "col_a" in MyTable._pxt_stored_columns
        assert "col_b" in MyTable._pxt_stored_columns
        assert MyTable._pxt_stored_columns["col_a"]["type"] is str
        assert MyTable._pxt_stored_columns["col_a"]["default"] is None

    def test_stored_column_with_default(self):
        sentinel = object()

        class MyTable(Model):
            __tablename__ = "test.defaults"
            col_a: str = sentinel

        assert MyTable._pxt_stored_columns["col_a"]["default"] is sentinel

    def test_computed_columns(self):
        proxy = Column.col_a

        class MyTable(Model):
            __tablename__ = "test.computed"
            col_a: str
            computed_col = proxy

        assert "computed_col" in MyTable._pxt_computed_columns
        assert MyTable._pxt_computed_columns["computed_col"] is proxy

    def test_declaration_order_preserved(self):
        class MyTable(Model):
            __tablename__ = "test.order"
            a: str
            b: int
            c: float

        assert list(MyTable._pxt_stored_columns.keys()) == ["a", "b", "c"]

    def test_primary_key(self):
        class MyTable(Model):
            __tablename__ = "test.pk"
            __primary_key__ = ["id"]
            id: str

        assert MyTable._pxt_primary_key == ["id"]

    def test_indexes(self):
        idx = EmbeddingIndex(Column.text, idx_name="test_idx")

        class MyTable(Model):
            __tablename__ = "test.indexed"
            text: str
            __indexes__ = [idx]

        assert MyTable._pxt_indexes == [idx]

    def test_registered_in_global_registry(self):
        class MyTable(Model):
            __tablename__ = "test.registered"
            col: str

        assert "test.registered" in _MODEL_REGISTRY
        assert _MODEL_REGISTRY["test.registered"] is MyTable

    def test_is_not_view(self):
        class MyTable(Model):
            __tablename__ = "test.not_view"
            col: str

        assert MyTable._pxt_is_view is False


class TestViewModelMeta:
    def test_is_view(self):
        class MyView(ViewModel):
            __tablename__ = "test.my_view"
            __base__ = "some_iterator_expr"

        assert MyView._pxt_is_view is True

    def test_view_base(self):
        base_expr = object()

        class MyView(ViewModel):
            __tablename__ = "test.view_base"
            __base__ = base_expr

        assert MyView._pxt_view_base is base_expr

    def test_view_with_filter(self):
        filter_expr = Column.status != None

        class MyView(ViewModel):
            __tablename__ = "test.filtered"
            __base__ = "iterator"
            __filter__ = filter_expr

        assert isinstance(MyView._pxt_view_filter, _FilterExpr)

    def test_computed_on_view(self):
        proxy = Column.audio_segment

        class MyView(ViewModel):
            __tablename__ = "test.view_computed"
            __base__ = "iterator"
            computed = proxy

        assert "computed" in MyView._pxt_computed_columns


# ---------------------------------------------------------------------------
# Cross-table column references
# ---------------------------------------------------------------------------

class TestCrossTableRef:
    def test_class_attr_returns_cross_ref(self):
        class Parent(Model):
            __tablename__ = "test.parent"
            video: str

        ref = Parent.video
        assert isinstance(ref, _CrossTableColumnRef)
        assert ref.model_cls is Parent
        assert ref.attr_name == "video"

    def test_chained_cross_ref(self):
        class Parent(Model):
            __tablename__ = "test.parent2"
            transcription: str

        ref = Parent.transcription.text
        assert isinstance(ref, _CrossTableColumnRef)
        assert ref.chain == [("attr", "text")]

    def test_unknown_attr_raises(self):
        class Parent(Model):
            __tablename__ = "test.parent3"
            known: str

        with pytest.raises(AttributeError, match="no column"):
            _ = Parent.unknown_col


# ---------------------------------------------------------------------------
# register_column (conditional schema)
# ---------------------------------------------------------------------------

class TestRegisterColumn:
    def test_register_on_model(self):
        class MyTable(Model):
            __tablename__ = "test.reg_model"
            col: str

        sentinel = object()
        MyTable.register_column("extra", sentinel)
        assert "extra" in MyTable._pxt_registered_columns
        assert MyTable._pxt_registered_columns["extra"] is sentinel

    def test_register_on_viewmodel(self):
        class MyView(ViewModel):
            __tablename__ = "test.reg_view"
            __base__ = "iter"

        sentinel = object()
        MyView.register_column("extra", sentinel)
        assert "extra" in MyView._pxt_registered_columns

    def test_registered_column_accessible_via_cross_ref(self):
        class MyTable(Model):
            __tablename__ = "test.reg_xref"
            col: str

        MyTable.register_column("dynamic_col", "some_expr")
        ref = MyTable.dynamic_col
        assert isinstance(ref, _CrossTableColumnRef)
        assert ref.attr_name == "dynamic_col"


# ---------------------------------------------------------------------------
# Model.where() returns _ViewBase
# ---------------------------------------------------------------------------

class TestModelWhere:
    def test_where_returns_viewbase(self):
        class Parent(Model):
            __tablename__ = "test.where_parent"
            status: str

        result = Parent.where(Column.status != None)
        assert isinstance(result, _ViewBase)
        assert result.model_cls is Parent


# ---------------------------------------------------------------------------
# Topological sort
# ---------------------------------------------------------------------------

class TestTopologicalSort:
    def test_independent_tables(self):
        class A(Model):
            __tablename__ = "test.a"
            x: str

        class B(Model):
            __tablename__ = "test.b"
            y: str

        classes = {"test.a": A, "test.b": B}
        result = _topological_sort(classes)
        assert set(result) == {A, B}

    def test_view_after_table(self):
        class Parent(Model):
            __tablename__ = "test.sort_parent"
            video: str

        class Child(ViewModel):
            __tablename__ = "test.sort_child"
            __base__ = Parent.video  # cross-table ref creates dependency

        classes = {"test.sort_parent": Parent, "test.sort_child": Child}
        result = _topological_sort(classes)
        assert result.index(Parent) < result.index(Child)

    def test_chain_dependency(self):
        class A(Model):
            __tablename__ = "test.chain_a"
            col: str

        class B(ViewModel):
            __tablename__ = "test.chain_b"
            __base__ = A.col

        B.register_column("col", "expr")

        class C(ViewModel):
            __tablename__ = "test.chain_c"
            __base__ = B.col

        classes = {
            "test.chain_a": A,
            "test.chain_b": B,
            "test.chain_c": C,
        }
        result = _topological_sort(classes)
        assert result.index(A) < result.index(B) < result.index(C)


# ---------------------------------------------------------------------------
# EmbeddingIndex
# ---------------------------------------------------------------------------

class TestEmbeddingIndex:
    def test_repr(self):
        idx = EmbeddingIndex(Column.text, idx_name="my_idx")
        assert "my_idx" in repr(idx)

    def test_with_string_embed(self):
        embed_fn = object()
        idx = EmbeddingIndex(
            Column.text,
            idx_name="text_idx",
            string_embed=embed_fn,
            metric="cosine",
        )
        assert idx.string_embed is embed_fn
        assert idx.metric == "cosine"

    def test_with_embedding(self):
        embed_fn = object()
        idx = EmbeddingIndex(
            Column.image,
            idx_name="img_idx",
            embedding=embed_fn,
        )
        assert idx.embedding is embed_fn


# ---------------------------------------------------------------------------
# list_models utility
# ---------------------------------------------------------------------------

class TestListModels:
    def test_list_all(self):
        class A(Model):
            __tablename__ = "ns1.a"
            x: str

        class B(Model):
            __tablename__ = "ns2.b"
            y: str

        result = list_models()
        assert "ns1.a" in result
        assert "ns2.b" in result

    def test_list_by_namespace(self):
        class A(Model):
            __tablename__ = "ns1.a"
            x: str

        class B(Model):
            __tablename__ = "ns2.b"
            y: str

        result = list_models("ns1")
        assert "ns1.a" in result
        assert "ns2.b" not in result


# ---------------------------------------------------------------------------
# create_all dry_run
# ---------------------------------------------------------------------------

class TestCreateAllDryRun:
    def test_dry_run_returns_order(self):
        class Parent(Model):
            __tablename__ = "dry.parent"
            video: str

        class Child(ViewModel):
            __tablename__ = "dry.child"
            __base__ = Parent.video

        result = create_all("dry", dry_run=True)
        assert result["order"] == ["dry.parent", "dry.child"]

    def test_dry_run_no_pxt_calls(self):
        class T(Model):
            __tablename__ = "dry2.table"
            col: str

        with patch.dict("sys.modules", {"pixeltable": MagicMock()}):
            result = create_all("dry2", dry_run=True)
            assert "dry2.table" in result["order"]


# ---------------------------------------------------------------------------
# Full create_all integration (mocked Pixeltable)
# ---------------------------------------------------------------------------

class TestCreateAllMocked:
    def test_creates_table_with_columns(self):
        uuid_fn = object()

        class MyTable(Model):
            __tablename__ = "mock.table1"
            __primary_key__ = ["uuid"]
            video: str
            uuid: str = uuid_fn
            timestamp: float

        mock_pxt = MagicMock()
        mock_table = MagicMock()
        mock_pxt.create_table.return_value = mock_table

        with patch.dict("sys.modules", {"pixeltable": mock_pxt}):
            result = create_all("mock")

        mock_pxt.create_dir.assert_called_once_with("mock", if_exists="ignore")
        mock_pxt.create_table.assert_called_once_with(
            "mock.table1",
            {"video": str, "uuid": uuid_fn, "timestamp": float},
            if_exists="ignore",
            primary_key=["uuid"],
        )

    def test_creates_computed_columns(self):
        class MyTable(Model):
            __tablename__ = "mock2.table"
            video: str

        mock_pxt = MagicMock()
        mock_table = MagicMock()
        mock_table.video = "resolved_video"
        mock_pxt.create_table.return_value = mock_table

        # The computed column expression is Column.video -- a proxy
        MyTable._pxt_computed_columns["audio"] = Column.video

        with patch.dict("sys.modules", {"pixeltable": mock_pxt}):
            create_all("mock2")

        mock_table.add_computed_column.assert_called_once_with(
            audio="resolved_video", if_exists="ignore"
        )

    def test_creates_embedding_index(self):
        embed_fn = object()

        class MyTable(Model):
            __tablename__ = "mock3.table"
            text: str
            __indexes__ = [
                EmbeddingIndex(Column.text, idx_name="test_idx", string_embed=embed_fn, metric="cosine")
            ]

        mock_pxt = MagicMock()
        mock_table = MagicMock()
        mock_pxt.create_table.return_value = mock_table

        with patch.dict("sys.modules", {"pixeltable": mock_pxt}):
            create_all("mock3")

        mock_table.add_embedding_index.assert_called_once_with(
            "text", if_exists="ignore", idx_name="test_idx", string_embed=embed_fn, metric="cosine"
        )

    def test_register_column_materialized(self):
        class MyTable(Model):
            __tablename__ = "mock4.table"
            col: str

        extra_expr = Column.col
        MyTable.register_column("derived", extra_expr)

        mock_pxt = MagicMock()
        mock_table = MagicMock()
        mock_table.col = "resolved_col"
        mock_pxt.create_table.return_value = mock_table

        with patch.dict("sys.modules", {"pixeltable": mock_pxt}):
            create_all("mock4")

        mock_table.add_computed_column.assert_called_once_with(
            derived="resolved_col", if_exists="ignore"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
