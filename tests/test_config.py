"""Test TOML configuration validity across all patterns and templates."""

from __future__ import annotations

import tomllib

import pytest

from tests.conftest import APPLICATION_FILE_TEMPLATES, PATTERNS, ROOT, SCHEMA_TEMPLATES, TEMPLATES


def _load_toml(path: str) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


class TestPatternPyprojectToml:
    """Validate pyproject.toml for each deployment pattern."""

    @pytest.mark.parametrize("pattern", PATTERNS)
    def test_toml_parses(self, pattern: str) -> None:
        cfg = _load_toml(str(ROOT / pattern / "pyproject.toml"))
        assert "project" in cfg
        assert "name" in cfg["project"]

    @pytest.mark.parametrize("pattern", PATTERNS)
    def test_requires_python(self, pattern: str) -> None:
        cfg = _load_toml(str(ROOT / pattern / "pyproject.toml"))
        assert cfg["project"].get("requires-python") == ">=3.11"

    @pytest.mark.parametrize("pattern", PATTERNS)
    def test_pixeltable_dependency(self, pattern: str) -> None:
        cfg = _load_toml(str(ROOT / pattern / "pyproject.toml"))
        deps = cfg["project"].get("dependencies", [])
        pxt_deps = [d for d in deps if d.startswith("pixeltable")]
        assert len(pxt_deps) > 0, f"{pattern} missing pixeltable dependency"

    @pytest.mark.parametrize("pattern", PATTERNS)
    def test_pixeltable_minimum_version(self, pattern: str) -> None:
        cfg = _load_toml(str(ROOT / pattern / "pyproject.toml"))
        deps = cfg["project"].get("dependencies", [])
        pxt_deps = [d for d in deps if d.startswith("pixeltable")]
        assert any(">=0.6.5" in d for d in pxt_deps), f"{pattern} must require pixeltable>=0.6.5, got {pxt_deps}"

    @pytest.mark.parametrize("template", TEMPLATES)
    def test_template_pixeltable_minimum_version(self, template: str) -> None:
        cfg = _load_toml(str(ROOT / "templates" / template / "pyproject.toml"))
        deps = cfg["project"].get("dependencies", [])
        pxt_deps = [d for d in deps if d.startswith("pixeltable")]
        assert len(pxt_deps) > 0, f"templates/{template} missing pixeltable dependency"
        assert any(">=0.6.5" in d for d in pxt_deps), (
            f"templates/{template} must require pixeltable>=0.6.5, got {pxt_deps}"
        )

    @pytest.mark.parametrize("template", TEMPLATES)
    def test_template_requires_python(self, template: str) -> None:
        cfg = _load_toml(str(ROOT / "templates" / template / "pyproject.toml"))
        assert cfg["project"].get("requires-python") == ">=3.11"


class TestProjectRoot:
    """pixeltable.toml marks a Pixeltable project root."""

    @pytest.mark.parametrize("pattern", PATTERNS)
    def test_pattern_has_pixeltable_toml(self, pattern: str) -> None:
        text = (ROOT / pattern / "pixeltable.toml").read_text(encoding="utf-8")
        assert "[[pixeltable.database]]" in text

    @pytest.mark.parametrize("template", TEMPLATES)
    def test_template_has_pixeltable_toml(self, template: str) -> None:
        text = (ROOT / "templates" / template / "pixeltable.toml").read_text(encoding="utf-8")
        assert "[[pixeltable.database]]" in text


class TestServingBuildSystem:
    """Application-file packages need [build-system] so app.py is importable."""

    @pytest.mark.parametrize("pattern", ["serving"])
    def test_pattern_has_build_system(self, pattern: str) -> None:
        cfg = _load_toml(str(ROOT / pattern / "pyproject.toml"))
        assert "build-system" in cfg, f"{pattern} missing [build-system]"
        assert "build-backend" in cfg["build-system"]

    @pytest.mark.parametrize("pattern", ["serving"])
    def test_pattern_has_py_modules(self, pattern: str) -> None:
        cfg = _load_toml(str(ROOT / pattern / "pyproject.toml"))
        setuptools = cfg.get("tool", {}).get("setuptools", {})
        assert "py-modules" in setuptools, f"{pattern} missing [tool.setuptools] py-modules"
        assert "app" in setuptools["py-modules"]

    @pytest.mark.parametrize("template", TEMPLATES)
    def test_template_has_build_system(self, template: str) -> None:
        cfg = _load_toml(str(ROOT / "templates" / template / "pyproject.toml"))
        assert "build-system" in cfg, f"templates/{template} missing [build-system]"

    @pytest.mark.parametrize("template", APPLICATION_FILE_TEMPLATES)
    def test_application_file_py_modules(self, template: str) -> None:
        cfg = _load_toml(str(ROOT / "templates" / template / "pyproject.toml"))
        setuptools = cfg.get("tool", {}).get("setuptools", {})
        assert "app" in setuptools.get("py-modules", []), f"templates/{template} py-modules must list app"

    @pytest.mark.parametrize("template", SCHEMA_TEMPLATES)
    def test_schema_template_py_modules(self, template: str) -> None:
        cfg = _load_toml(str(ROOT / "templates" / template / "pyproject.toml"))
        setuptools = cfg.get("tool", {}).get("setuptools", {})
        assert "schema" in setuptools.get("py-modules", []), f"templates/{template} py-modules must list schema"


class TestNoTomlService:
    """[[tool.pixeltable.service]] is gone. Routes live on FastAPIRouter."""

    @pytest.mark.parametrize("pattern", PATTERNS)
    def test_pattern_has_no_service_table(self, pattern: str) -> None:
        cfg = _load_toml(str(ROOT / pattern / "pyproject.toml"))
        services = cfg.get("tool", {}).get("pixeltable", {}).get("service")
        assert not services, f"{pattern} still has [tool.pixeltable.service]"

    @pytest.mark.parametrize("template", TEMPLATES)
    def test_template_has_no_service_table(self, template: str) -> None:
        cfg = _load_toml(str(ROOT / "templates" / template / "pyproject.toml"))
        services = cfg.get("tool", {}).get("pixeltable", {}).get("service")
        assert not services, f"templates/{template} still has [tool.pixeltable.service]"
