"""Declarative schema layer for Pixeltable.

Provides pxt.Model, pxt.ViewModel, Column sentinel, and create_all()
as a class-based alternative to the imperative create_table/add_computed_column API.

This module is a standalone prototype -- it wraps the real Pixeltable API
and can be tested independently.
"""

import sys
from collections import OrderedDict
from typing import Any


# ---------------------------------------------------------------------------
# Column sentinel -- deferred column reference for use inside class bodies
# ---------------------------------------------------------------------------

class _ColumnProxy:
    """Proxy object returned by Column.<name> that records attribute chains.

    Supports arbitrary depth: Column.final_response.content[0].text
    The chain is stored as a list of (op, key) tuples:
      - ("attr", "name")   for .name
      - ("item", 0)        for [0]
    """

    def __init__(self, name: str, chain: list[tuple[str, Any]] | None = None):
        object.__setattr__(self, "_name", name)
        object.__setattr__(self, "_chain", chain or [])

    def __getattr__(self, attr: str) -> "_ColumnProxy":
        if attr.startswith("_"):
            raise AttributeError(attr)
        new_chain = list(self._chain) + [("attr", attr)]
        return _ColumnProxy(self._name, new_chain)

    def __getitem__(self, key: Any) -> "_ColumnProxy":
        new_chain = list(self._chain) + [("item", key)]
        return _ColumnProxy(self._name, new_chain)

    def __eq__(self, other: Any) -> "_FilterExpr":
        return _FilterExpr("eq", self, other)

    def __ne__(self, other: Any) -> "_FilterExpr":
        return _FilterExpr("ne", self, other)

    def __gt__(self, other: Any) -> "_FilterExpr":
        return _FilterExpr("gt", self, other)

    def __lt__(self, other: Any) -> "_FilterExpr":
        return _FilterExpr("lt", self, other)

    def __ge__(self, other: Any) -> "_FilterExpr":
        return _FilterExpr("ge", self, other)

    def __le__(self, other: Any) -> "_FilterExpr":
        return _FilterExpr("le", self, other)

    def __mod__(self, other: Any) -> "_ColumnProxy":
        new_chain = list(self._chain) + [("mod", other)]
        return _ColumnProxy(self._name, new_chain)

    def __add__(self, other: Any) -> "_ColumnProxy":
        new_chain = list(self._chain) + [("add", other)]
        return _ColumnProxy(self._name, new_chain)

    def __repr__(self) -> str:
        parts = [f"Column.{self._name}"]
        for op, key in self._chain:
            if op == "attr":
                parts.append(f".{key}")
            elif op == "item":
                parts.append(f"[{key!r}]")
            else:
                parts.append(f".{op}({key!r})")
        return "".join(parts)

    def resolve(self, table: Any) -> Any:
        """Resolve this proxy against a real Pixeltable table object."""
        col = getattr(table, self._name)
        for op, key in self._chain:
            if op == "attr":
                col = getattr(col, key)
            elif op == "item":
                col = col[key]
            elif op == "mod":
                col = col % key
            elif op == "add":
                col = col + key
        return col


class _ColumnSentinel:
    """Singleton accessed as `Column.video`, `Column.text`, etc.

    Each attribute access returns a _ColumnProxy that records the name
    for later resolution by the metaclass.
    """

    def __getattr__(self, name: str) -> _ColumnProxy:
        if name.startswith("_"):
            raise AttributeError(name)
        return _ColumnProxy(name)


Column = _ColumnSentinel()


# ---------------------------------------------------------------------------
# Filter expression (deferred boolean expressions for __filter__)
# ---------------------------------------------------------------------------

class _FilterExpr:
    """Deferred boolean expression for view filters."""

    def __init__(self, op: str, left: Any, right: Any):
        self.op = op
        self.left = left
        self.right = right

    def __and__(self, other: "_FilterExpr") -> "_FilterExpr":
        return _FilterExpr("and", self, other)

    def __or__(self, other: "_FilterExpr") -> "_FilterExpr":
        return _FilterExpr("or", self, other)

    def __repr__(self) -> str:
        return f"_FilterExpr({self.op}, {self.left!r}, {self.right!r})"

    def resolve(self, table: Any) -> Any:
        """Resolve against a real Pixeltable table to produce a filter expression."""
        left = self.left.resolve(table) if hasattr(self.left, "resolve") else self.left
        right = self.right.resolve(table) if hasattr(self.right, "resolve") else self.right

        ops = {
            "eq": lambda l, r: l == r,
            "ne": lambda l, r: l != r,
            "gt": lambda l, r: l > r,
            "lt": lambda l, r: l < r,
            "ge": lambda l, r: l >= r,
            "le": lambda l, r: l <= r,
            "and": lambda l, r: l & r,
            "or": lambda l, r: l | r,
        }
        return ops[self.op](left, right)


# ---------------------------------------------------------------------------
# Deferred computed column expression
# ---------------------------------------------------------------------------

class _ComputedColumnExpr:
    """Wraps a callable + args/kwargs where some args are _ColumnProxy instances.

    At create_all() time, proxies are resolved against the real table and
    the function is called to produce the actual Pixeltable expression.
    """

    def __init__(self, func: Any, args: tuple, kwargs: dict):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def resolve(self, table: Any) -> Any:
        """Resolve all _ColumnProxy args against the table, then call func."""
        resolved_args = tuple(
            a.resolve(table) if isinstance(a, _ColumnProxy) else a
            for a in self.args
        )
        resolved_kwargs = {
            k: v.resolve(table) if isinstance(v, _ColumnProxy) else v
            for k, v in self.kwargs.items()
        }
        return self.func(*resolved_args, **resolved_kwargs)

    def __repr__(self) -> str:
        return f"_ComputedColumnExpr({self.func.__name__}, args={self.args}, kwargs={self.kwargs})"


# ---------------------------------------------------------------------------
# Embedding index descriptor
# ---------------------------------------------------------------------------

class EmbeddingIndex:
    """Declarative embedding index descriptor for use in __indexes__."""

    def __init__(
        self,
        column: _ColumnProxy | str,
        *,
        idx_name: str | None = None,
        embedding: Any = None,
        string_embed: Any = None,
        metric: str = "cosine",
    ):
        self.column = column
        self.idx_name = idx_name
        self.embedding = embedding
        self.string_embed = string_embed
        self.metric = metric

    def __repr__(self) -> str:
        return f"EmbeddingIndex({self.column!r}, idx_name={self.idx_name!r})"


# ---------------------------------------------------------------------------
# Cross-table column reference
# ---------------------------------------------------------------------------

class _CrossTableColumnRef:
    """Returned by ModelClass.column_name -- a deferred cross-table reference.

    Records the source model class and column name so create_all() can
    resolve it once the parent table is materialized.
    """

    def __init__(self, model_cls: type, attr_name: str, chain: list[tuple[str, Any]] | None = None):
        self.model_cls = model_cls
        self.attr_name = attr_name
        self.chain = chain or []

    def __getattr__(self, name: str) -> "_CrossTableColumnRef":
        if name.startswith("_"):
            raise AttributeError(name)
        return _CrossTableColumnRef(self.model_cls, self.attr_name, self.chain + [("attr", name)])

    def __getitem__(self, key: Any) -> "_CrossTableColumnRef":
        return _CrossTableColumnRef(self.model_cls, self.attr_name, self.chain + [("item", key)])

    def __eq__(self, other: Any) -> "_FilterExpr":
        return _FilterExpr("eq", self, other)

    def __ne__(self, other: Any) -> "_FilterExpr":
        return _FilterExpr("ne", self, other)

    def __repr__(self) -> str:
        parts = [f"{self.model_cls.__name__}.{self.attr_name}"]
        for op, key in self.chain:
            if op == "attr":
                parts.append(f".{key}")
            elif op == "item":
                parts.append(f"[{key!r}]")
        return "".join(parts)

    def resolve(self, tables: dict[str, Any]) -> Any:
        """Resolve against the materialized tables dict."""
        tablename = self.model_cls._pxt_tablename
        table = tables[tablename]
        col = getattr(table, self.attr_name)
        for op, key in self.chain:
            if op == "attr":
                col = getattr(col, key)
            elif op == "item":
                col = col[key]
        return col


# ---------------------------------------------------------------------------
# Model registry -- tracks all declared Model/ViewModel classes
# ---------------------------------------------------------------------------

_MODEL_REGISTRY: dict[str, type] = OrderedDict()


# ---------------------------------------------------------------------------
# Metaclass
# ---------------------------------------------------------------------------

# Attributes that are part of the declarative DSL, not user columns
_RESERVED_ATTRS = frozenset({
    "__tablename__", "__primary_key__", "__indexes__",
    "__base__", "__parent__", "__filter__", "__iterator__",
    "__module__", "__qualname__", "__doc__",
})


class _ModelMeta(type):
    """Metaclass for Model and ViewModel.

    At class creation time, inspects annotations and assignments to build:
      - _pxt_stored_columns: dict of {name: type_annotation} for stored columns
      - _pxt_computed_columns: OrderedDict of {name: expression} for computed columns
      - _pxt_indexes: list of EmbeddingIndex
      - _pxt_tablename: fully qualified table name
      - _pxt_primary_key: list of PK column names
      - _pxt_is_view: bool
    """

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> type:
        # Skip processing for the base Model/ViewModel classes themselves
        if name in ("Model", "ViewModel"):
            return super().__new__(mcs, name, bases, namespace)

        annotations = namespace.get("__annotations__", {})
        stored_columns: dict[str, Any] = OrderedDict()
        computed_columns: OrderedDict[str, Any] = OrderedDict()

        # Determine if this is a view
        is_view = any(
            hasattr(b, "_pxt_is_view") and b._pxt_is_view
            for b in bases
            if hasattr(b, "_pxt_is_view")
        ) or "__base__" in namespace

        for attr_name, type_hint in annotations.items():
            if attr_name.startswith("_"):
                continue
            default = namespace.get(attr_name)
            stored_columns[attr_name] = {
                "type": type_hint,
                "default": default,
            }

        # Identify computed columns: assignments that aren't type-annotated
        # and aren't reserved/private/dunder.
        # Also scan mixin bases (non-Model/ViewModel) for contributed columns.
        def _is_computed(attr_name: str, value: Any) -> bool:
            if attr_name.startswith("_") or attr_name in _RESERVED_ATTRS:
                return False
            if attr_name in annotations:
                return False
            if callable(value) and not isinstance(value, (_ColumnProxy, _ComputedColumnExpr, _CrossTableColumnRef)):
                return False
            return True

        # Mixin bases first (so class body can override)
        for base in bases:
            if base in (Model, ViewModel) or isinstance(base, _ModelMeta):
                continue
            for attr_name in vars(base):
                value = getattr(base, attr_name)
                if _is_computed(attr_name, value) and attr_name not in namespace:
                    computed_columns[attr_name] = value

        # Class body (overrides mixin values)
        for attr_name, value in namespace.items():
            if _is_computed(attr_name, value):
                computed_columns[attr_name] = value

        tablename = namespace.get("__tablename__")
        primary_key = namespace.get("__primary_key__")
        indexes = namespace.get("__indexes__", [])

        # View-specific
        view_base = namespace.get("__base__")
        view_parent = namespace.get("__parent__")
        view_filter = namespace.get("__filter__")
        view_iterator = namespace.get("__iterator__")

        cls = super().__new__(mcs, name, bases, namespace)

        cls._pxt_stored_columns = stored_columns
        cls._pxt_computed_columns = computed_columns
        cls._pxt_tablename = tablename
        cls._pxt_primary_key = primary_key
        cls._pxt_indexes = indexes
        cls._pxt_is_view = is_view
        cls._pxt_view_base = view_base
        cls._pxt_view_parent = view_parent
        cls._pxt_view_filter = view_filter
        cls._pxt_view_iterator = view_iterator
        cls._pxt_registered_columns: OrderedDict[str, Any] = OrderedDict()
        cls._pxt_table = None  # populated by create_all()

        # Remove computed column attrs from the class so that
        # OtherModel.computed_col routes through __getattr__ and
        # returns a _CrossTableColumnRef instead of the raw expression.
        for col_name in computed_columns:
            try:
                delattr(cls, col_name)
            except AttributeError:
                pass

        if tablename:
            _MODEL_REGISTRY[tablename] = cls

        return cls

    def __getattr__(cls, name: str) -> _CrossTableColumnRef:
        """Allow OtherModel.column_name to return a cross-table ref."""
        if name.startswith("_"):
            raise AttributeError(name)
        if hasattr(cls, "_pxt_stored_columns") and (
            name in cls._pxt_stored_columns
            or name in cls._pxt_computed_columns
            or name in cls._pxt_registered_columns
        ):
            return _CrossTableColumnRef(cls, name)
        raise AttributeError(f"{cls.__name__} has no column {name!r}")


# ---------------------------------------------------------------------------
# Base classes
# ---------------------------------------------------------------------------

class Model(metaclass=_ModelMeta):
    """Declarative base for Pixeltable tables.

    Usage:
        class Videos(Model):
            __tablename__ = "videointel.videos"
            __primary_key__ = ["uuid"]

            video: pxt.Video
            title: pxt.String
            uuid: pxt.String = uuid7()
            timestamp: pxt.Timestamp

            audio = extract_audio(Column.video, format="mp3")
    """

    _pxt_is_view = False

    @classmethod
    def register_column(cls, name: str, expr: Any) -> None:
        """Post-class-definition escape hatch for conditional columns.

        Usage:
            if HAS_OPENAI:
                MyModel.register_column("transcription", openai.transcriptions(...))
        """
        cls._pxt_registered_columns[name] = expr

    @classmethod
    def where(cls, condition: Any) -> "_ViewBase":
        """Return a filterable reference for use in ViewModel.__base__."""
        return _ViewBase(cls, filter_expr=condition)


class ViewModel(metaclass=_ModelMeta):
    """Declarative base for Pixeltable views.

    Usage:
        class Frames(ViewModel):
            __base__ = frame_iterator(video=Videos.video, fps=1.0)

            thumbnail = pxt_image.b64_encode(
                pxt_image.thumbnail(Column.frame, size=(320, 320)))

            __indexes__ = [
                EmbeddingIndex(Column.frame, idx_name="frames_clip_idx",
                               embedding=clip_embed)
            ]
    """

    _pxt_is_view = True

    @classmethod
    def register_column(cls, name: str, expr: Any) -> None:
        """Post-class-definition escape hatch for conditional columns."""
        cls._pxt_registered_columns[name] = expr

    @classmethod
    def where(cls, condition: Any) -> "_ViewBase":
        """Return a filterable reference for use as another ViewModel's parent."""
        return _ViewBase(cls, filter_expr=condition)


# ---------------------------------------------------------------------------
# _ViewBase -- returned by Model.where() / ViewModel.where()
# ---------------------------------------------------------------------------

class _ViewBase:
    """Intermediate object representing a filtered table/view for use as __base__."""

    def __init__(self, model_cls: type, filter_expr: Any = None):
        self.model_cls = model_cls
        self.filter_expr = filter_expr

    def __repr__(self) -> str:
        return f"_ViewBase({self.model_cls.__name__}, filter={self.filter_expr!r})"


# ---------------------------------------------------------------------------
# create_all() -- topological sort + materialization
# ---------------------------------------------------------------------------

def _extract_namespace(tablename: str) -> str:
    """Extract namespace prefix from a fully qualified table name."""
    parts = tablename.rsplit(".", 1)
    return parts[0] if len(parts) > 1 else ""


def _get_dependencies(cls: type) -> set[str]:
    """Extract table names that cls depends on (via __base__, __parent__, cross-table refs)."""
    deps: set[str] = set()

    # View dependencies from __base__
    view_base = getattr(cls, "_pxt_view_base", None)
    if view_base is not None:
        if isinstance(view_base, _ViewBase):
            dep_cls = view_base.model_cls
            if hasattr(dep_cls, "_pxt_tablename") and dep_cls._pxt_tablename:
                deps.add(dep_cls._pxt_tablename)

    # __parent__ dependency
    view_parent = getattr(cls, "_pxt_view_parent", None)
    if view_parent is not None and hasattr(view_parent, "_pxt_tablename"):
        deps.add(view_parent._pxt_tablename)

    # Scan computed columns and __base__ for _CrossTableColumnRef
    for value in list(cls._pxt_computed_columns.values()) + [view_base]:
        _collect_cross_refs(value, deps)

    return deps


def _collect_cross_refs(obj: Any, deps: set[str]) -> None:
    """Recursively find _CrossTableColumnRef instances in an expression tree."""
    if isinstance(obj, _CrossTableColumnRef):
        if hasattr(obj.model_cls, "_pxt_tablename") and obj.model_cls._pxt_tablename:
            deps.add(obj.model_cls._pxt_tablename)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            _collect_cross_refs(item, deps)
    elif isinstance(obj, dict):
        for v in obj.values():
            _collect_cross_refs(v, deps)


def _topological_sort(classes: dict[str, type]) -> list[type]:
    """Sort model classes so dependencies come before dependents."""
    sorted_list: list[type] = []
    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(name: str) -> None:
        if name in visited:
            return
        if name in visiting:
            raise ValueError(f"Circular dependency detected involving {name}")
        visiting.add(name)

        cls = classes[name]
        for dep in _get_dependencies(cls):
            if dep in classes:
                visit(dep)

        visiting.discard(name)
        visited.add(name)
        sorted_list.append(cls)

    for name in classes:
        visit(name)

    return sorted_list


def _resolve_expr_deep(expr: Any, table: Any, tables: dict[str, Any]) -> Any:
    """Resolve _ColumnProxy and _CrossTableColumnRef instances in an expression."""
    if isinstance(expr, _ColumnProxy):
        return expr.resolve(table)
    if isinstance(expr, _CrossTableColumnRef):
        return expr.resolve(tables)
    if isinstance(expr, _ComputedColumnExpr):
        resolved_args = tuple(_resolve_expr_deep(a, table, tables) for a in expr.args)
        resolved_kwargs = {k: _resolve_expr_deep(v, table, tables) for k, v in expr.kwargs.items()}
        return expr.func(*resolved_args, **resolved_kwargs)
    if isinstance(expr, dict):
        return {k: _resolve_expr_deep(v, table, tables) for k, v in expr.items()}
    if isinstance(expr, (list, tuple)):
        resolved = [_resolve_expr_deep(item, table, tables) for item in expr]
        return type(expr)(resolved)
    return expr


def create_all(namespace: str | None = None, *, checkfirst: bool = True, dry_run: bool = False) -> dict[str, Any]:
    """Materialize all registered Model/ViewModel classes into Pixeltable tables.

    Args:
        namespace: If given, only create models whose __tablename__ starts with this prefix.
        checkfirst: If True, use if_exists="ignore" (default). If False, fail on existing.
        dry_run: If True, return the execution plan without calling Pixeltable.

    Returns:
        Dict mapping tablename -> materialized Pixeltable table/view object.
    """
    import pixeltable as pxt

    if_exists = "ignore" if checkfirst else "error"

    # Filter to namespace
    candidates = {
        name: cls for name, cls in _MODEL_REGISTRY.items()
        if namespace is None or name.startswith(f"{namespace}.")
    }

    sorted_classes = _topological_sort(candidates)
    tables: dict[str, Any] = {}

    if dry_run:
        return {
            "order": [cls._pxt_tablename for cls in sorted_classes],
            "classes": {cls._pxt_tablename: cls for cls in sorted_classes},
        }

    # Ensure namespace directory exists
    if namespace:
        pxt.create_dir(namespace, if_exists="ignore")

    for cls in sorted_classes:
        tablename = cls._pxt_tablename

        if cls._pxt_is_view:
            table = _materialize_view(cls, tables, if_exists, pxt)
        else:
            table = _materialize_table(cls, tables, if_exists, pxt)

        tables[tablename] = table
        cls._pxt_table = table

    return tables


def _materialize_table(cls: type, tables: dict[str, Any], if_exists: str, pxt: Any) -> Any:
    """Create a Pixeltable table from a Model class."""
    tablename = cls._pxt_tablename

    # Build column schema dict
    schema: dict[str, Any] = {}
    for col_name, col_info in cls._pxt_stored_columns.items():
        col_type = col_info["type"]
        default = col_info["default"]
        schema[col_name] = default if default is not None else col_type

    pk = cls._pxt_primary_key
    kwargs: dict[str, Any] = {"if_exists": if_exists}
    if pk:
        kwargs["primary_key"] = pk

    table = pxt.create_table(tablename, schema, **kwargs)

    # Add computed columns (in declaration order)
    all_computed = OrderedDict(cls._pxt_computed_columns)
    all_computed.update(cls._pxt_registered_columns)

    for col_name, expr in all_computed.items():
        resolved = _resolve_expr_deep(expr, table, tables)
        table.add_computed_column(**{col_name: resolved}, if_exists=if_exists)

    # Add embedding indexes
    for idx in cls._pxt_indexes:
        col_ref = idx.column
        col_name = col_ref._name if isinstance(col_ref, _ColumnProxy) else col_ref
        idx_kwargs: dict[str, Any] = {"if_exists": if_exists}
        if idx.idx_name:
            idx_kwargs["idx_name"] = idx.idx_name
        if idx.embedding:
            idx_kwargs["embedding"] = idx.embedding
        if idx.string_embed:
            idx_kwargs["string_embed"] = idx.string_embed
        if idx.metric:
            idx_kwargs["metric"] = idx.metric
        table.add_embedding_index(col_name, **idx_kwargs)

    return table


def _materialize_view(cls: type, tables: dict[str, Any], if_exists: str, pxt: Any) -> Any:
    """Create a Pixeltable view from a ViewModel class."""
    tablename = cls._pxt_tablename

    view_base = cls._pxt_view_base
    view_parent = cls._pxt_view_parent
    view_filter = cls._pxt_view_filter
    view_iterator = cls._pxt_view_iterator

    parent_table = None
    iterator_expr = None
    filter_expr = None

    if isinstance(view_base, _ViewBase):
        # __base__ = SomeModel.where(condition)
        parent_cls = view_base.model_cls
        parent_table = tables[parent_cls._pxt_tablename]
        if view_base.filter_expr is not None:
            filter_expr = view_base.filter_expr

        if view_iterator:
            iterator_expr = _resolve_expr_deep(view_iterator, parent_table, tables)
    else:
        # __base__ is an iterator expression directly (the common case)
        # Need to find the parent from cross-table refs in the expression
        parent_cls = _find_parent_in_expr(view_base)
        if parent_cls:
            parent_table = tables[parent_cls._pxt_tablename]
            iterator_expr = _resolve_expr_deep(view_base, parent_table, tables)
        else:
            iterator_expr = view_base

    # Handle explicit __parent__ + __filter__
    if view_parent is not None:
        parent_table = tables[view_parent._pxt_tablename]
    if view_filter is not None:
        if isinstance(view_filter, _FilterExpr):
            filter_expr = view_filter.resolve(parent_table)
        else:
            filter_expr = _resolve_expr_deep(view_filter, parent_table, tables)

    # Apply filter to parent if needed
    actual_parent = parent_table
    if filter_expr is not None:
        actual_parent = parent_table.where(filter_expr)

    view = pxt.create_view(
        tablename,
        actual_parent,
        iterator=iterator_expr,
        if_exists=if_exists,
    )

    # Add computed columns
    all_computed = OrderedDict(cls._pxt_computed_columns)
    all_computed.update(cls._pxt_registered_columns)

    for col_name, expr in all_computed.items():
        resolved = _resolve_expr_deep(expr, view, tables)
        view.add_computed_column(**{col_name: resolved}, if_exists=if_exists)

    # Add embedding indexes
    for idx in cls._pxt_indexes:
        col_ref = idx.column
        col_name = col_ref._name if isinstance(col_ref, _ColumnProxy) else col_ref
        idx_kwargs: dict[str, Any] = {"if_exists": if_exists}
        if idx.idx_name:
            idx_kwargs["idx_name"] = idx.idx_name
        if idx.embedding:
            idx_kwargs["embedding"] = idx.embedding
        if idx.string_embed:
            idx_kwargs["string_embed"] = idx.string_embed
        if idx.metric:
            idx_kwargs["metric"] = idx.metric
        view.add_embedding_index(col_name, **idx_kwargs)

    return view


def _find_parent_in_expr(expr: Any) -> type | None:
    """Walk an expression tree to find the first _CrossTableColumnRef's model class."""
    if isinstance(expr, _CrossTableColumnRef):
        return expr.model_cls
    if isinstance(expr, (list, tuple)):
        for item in expr:
            found = _find_parent_in_expr(item)
            if found:
                return found
    if isinstance(expr, dict):
        for v in expr.values():
            found = _find_parent_in_expr(v)
            if found:
                return found
    # Check function arguments if this is a functools.partial or similar
    if hasattr(expr, "args"):
        for arg in expr.args:
            found = _find_parent_in_expr(arg)
            if found:
                return found
    if hasattr(expr, "keywords"):
        for v in expr.keywords.values():
            found = _find_parent_in_expr(v)
            if found:
                return found
    return None


# ---------------------------------------------------------------------------
# Utility: list all registered models
# ---------------------------------------------------------------------------

def list_models(namespace: str | None = None) -> dict[str, type]:
    """Return all registered model classes, optionally filtered by namespace."""
    if namespace is None:
        return dict(_MODEL_REGISTRY)
    return {
        name: cls for name, cls in _MODEL_REGISTRY.items()
        if name.startswith(f"{namespace}.")
    }


def clear_registry() -> None:
    """Clear the model registry (useful for tests)."""
    _MODEL_REGISTRY.clear()
