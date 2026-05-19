"""Test application template integrity."""

from __future__ import annotations

import ast
import sys

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef]

from tests.conftest import ROOT, TEMPLATES


def _load_toml(path: str) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


class TestTemplateIntegrity:
    """Each template is a self-contained, valid project."""

    @pytest.mark.parametrize("template", TEMPLATES)
    def test_schema_defines_pxt_queries(self, template: str) -> None:
        """schema.py should contain @pxt.query decorated functions."""
        schema_path = ROOT / "templates" / template / "schema.py"
        source = schema_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(schema_path))
        func_names = [node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        assert len(func_names) > 0, f"templates/{template}/schema.py has no functions"

    @pytest.mark.parametrize("template", TEMPLATES)
    def test_query_routes_reference_existing_functions(self, template: str) -> None:
        """Query routes in TOML should reference functions that exist in schema.py."""
        toml_path = ROOT / "templates" / template / "pyproject.toml"
        cfg = _load_toml(str(toml_path))
        routes = cfg.get("tool", {}).get("pixeltable", {}).get("service", [{}])[0].get("routes", [])
        query_attrs = []
        for route in routes:
            if route.get("type") == "query":
                _, _, attr = route["query"].partition(":")
                query_attrs.append(attr)

        if not query_attrs:
            return

        schema_path = ROOT / "templates" / template / "schema.py"
        source = schema_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(schema_path))
        defined_funcs = {
            node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        for attr in query_attrs:
            assert attr in defined_funcs, (
                f"templates/{template}: route references '{attr}' but schema.py only defines {sorted(defined_funcs)}"
            )

    @pytest.mark.parametrize("template", TEMPLATES)
    def test_no_deploy_directories(self, template: str) -> None:
        """Templates should not include deploy/ directories (those live at repo root)."""
        deploy_dir = ROOT / "templates" / template / "deploy"
        assert not deploy_dir.exists(), f"templates/{template} should not ship deploy/"

    @pytest.mark.parametrize("template", TEMPLATES)
    def test_pixeltable_namespace_consistency(self, template: str) -> None:
        """The pxt namespace in schema.py should match the service name or table paths in TOML."""
        toml_path = ROOT / "templates" / template / "pyproject.toml"
        cfg = _load_toml(str(toml_path))
        routes = cfg.get("tool", {}).get("pixeltable", {}).get("service", [{}])[0].get("routes", [])
        table_namespaces = set()
        for route in routes:
            table = route.get("table", "")
            if "." in table:
                table_namespaces.add(table.split(".")[0])

        if not table_namespaces:
            return

        schema_path = ROOT / "templates" / template / "schema.py"
        source = schema_path.read_text(encoding="utf-8")
        for ns in table_namespaces:
            assert ns in source, (
                f"templates/{template}: TOML routes reference namespace '{ns}' but it doesn't appear in schema.py"
            )
