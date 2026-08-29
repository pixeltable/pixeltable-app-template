"""Test application template integrity."""

from __future__ import annotations

import ast

import pytest

from tests.conftest import APPLICATION_FILE_TEMPLATES, ROOT, SCHEMA_TEMPLATES, TEMPLATES


class TestTemplateIntegrity:
    """Each template is a self-contained, valid project."""

    @pytest.mark.parametrize("template", SCHEMA_TEMPLATES)
    def test_schema_defines_pxt_queries(self, template: str) -> None:
        schema_path = ROOT / "templates" / template / "schema.py"
        source = schema_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(schema_path))
        func_names = [node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        assert len(func_names) > 0, f"templates/{template}/schema.py has no functions"

    @pytest.mark.parametrize("template", APPLICATION_FILE_TEMPLATES)
    def test_app_defines_tablemodel_and_router(self, template: str) -> None:
        app_path = ROOT / "templates" / template / "app.py"
        source = app_path.read_text(encoding="utf-8")
        assert "model_base()" in source, f"templates/{template}/app.py must declare TableModel = pxt.model_base()"
        assert "FastAPIRouter" in source, f"templates/{template}/app.py must declare a FastAPIRouter"
        assert "__indexes__" in source or template == "media-indexing", (
            f"templates/{template}/app.py should declare indexes on the model"
        )
        assert "add_embedding_index" not in source
        assert "pxt.create_table" not in source

    @pytest.mark.parametrize("template", APPLICATION_FILE_TEMPLATES)
    def test_app_defines_pxt_queries(self, template: str) -> None:
        app_path = ROOT / "templates" / template / "app.py"
        source = app_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(app_path))
        func_names = [node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        assert len(func_names) > 0, f"templates/{template}/app.py has no functions"

    @pytest.mark.parametrize("template", TEMPLATES)
    def test_no_deploy_directories(self, template: str) -> None:
        deploy_dir = ROOT / "templates" / template / "deploy"
        assert not deploy_dir.exists(), f"templates/{template} should not ship deploy/"
