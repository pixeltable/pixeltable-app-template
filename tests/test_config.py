"""Test TOML configuration validity across all patterns and templates."""

from __future__ import annotations

import sys

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef]

from tests.conftest import PATTERNS, ROOT, TEMPLATES

# Patterns that use `pxt serve` and need [build-system] for schema importability.
SERVING_PATTERNS = ["serving"]
SERVING_TEMPLATES = TEMPLATES


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
        assert "requires-python" in cfg["project"]

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


class TestServingBuildSystem:
    """Patterns/templates using `pxt serve` need [build-system] for schema importability."""

    @pytest.mark.parametrize("pattern", SERVING_PATTERNS)
    def test_pattern_has_build_system(self, pattern: str) -> None:
        cfg = _load_toml(str(ROOT / pattern / "pyproject.toml"))
        assert "build-system" in cfg, f"{pattern} missing [build-system]"
        assert "build-backend" in cfg["build-system"]

    @pytest.mark.parametrize("pattern", SERVING_PATTERNS)
    def test_pattern_has_py_modules(self, pattern: str) -> None:
        cfg = _load_toml(str(ROOT / pattern / "pyproject.toml"))
        setuptools = cfg.get("tool", {}).get("setuptools", {})
        assert "py-modules" in setuptools, f"{pattern} missing [tool.setuptools] py-modules"
        assert "schema" in setuptools["py-modules"]

    @pytest.mark.parametrize("template", SERVING_TEMPLATES)
    def test_template_has_build_system(self, template: str) -> None:
        cfg = _load_toml(str(ROOT / "templates" / template / "pyproject.toml"))
        assert "build-system" in cfg, f"templates/{template} missing [build-system]"

    @pytest.mark.parametrize("template", SERVING_TEMPLATES)
    def test_template_has_py_modules(self, template: str) -> None:
        cfg = _load_toml(str(ROOT / "templates" / template / "pyproject.toml"))
        setuptools = cfg.get("tool", {}).get("setuptools", {})
        assert "py-modules" in setuptools, f"templates/{template} missing py-modules"
        assert "schema" in setuptools["py-modules"]


class TestPxtServeConfig:
    """Validate [tool.pixeltable.service] route configs."""

    def _get_service_config(self, toml_path: str) -> dict | None:
        cfg = _load_toml(toml_path)
        services = cfg.get("tool", {}).get("pixeltable", {}).get("service", [])
        return services[0] if services else None

    def _get_routes(self, toml_path: str) -> list[dict]:
        service = self._get_service_config(toml_path)
        return service.get("routes", []) if service else []

    @pytest.mark.parametrize("pattern", SERVING_PATTERNS)
    def test_pattern_has_service_config(self, pattern: str) -> None:
        svc = self._get_service_config(str(ROOT / pattern / "pyproject.toml"))
        assert svc is not None, f"{pattern} missing [[tool.pixeltable.service]]"
        assert "name" in svc

    @pytest.mark.parametrize("pattern", SERVING_PATTERNS)
    def test_pattern_routes_have_paths(self, pattern: str) -> None:
        routes = self._get_routes(str(ROOT / pattern / "pyproject.toml"))
        assert len(routes) > 0, f"{pattern} has no routes"
        for route in routes:
            assert "path" in route, f"Route missing path in {pattern}"
            assert route["path"].startswith("/"), f"Route path must start with / in {pattern}"

    @pytest.mark.parametrize("pattern", SERVING_PATTERNS)
    def test_query_routes_use_colon_format(self, pattern: str) -> None:
        """0.6.2+ uses module:attribute format for query references."""
        routes = self._get_routes(str(ROOT / pattern / "pyproject.toml"))
        for route in routes:
            if route.get("type") == "query":
                query = route["query"]
                assert ":" in query, f"Query {query!r} should use module:attribute format"
                module, _, attr = query.partition(":")
                assert module, f"Query {query!r} missing module name"
                assert attr, f"Query {query!r} missing attribute name"

    @pytest.mark.parametrize("template", SERVING_TEMPLATES)
    def test_template_has_service_config(self, template: str) -> None:
        svc = self._get_service_config(str(ROOT / "templates" / template / "pyproject.toml"))
        assert svc is not None, f"templates/{template} missing [[tool.pixeltable.service]]"

    @pytest.mark.parametrize("template", SERVING_TEMPLATES)
    def test_template_query_routes_use_colon_format(self, template: str) -> None:
        routes = self._get_routes(str(ROOT / "templates" / template / "pyproject.toml"))
        for route in routes:
            if route.get("type") == "query":
                query = route["query"]
                assert ":" in query, f"Query {query!r} in templates/{template} should use module:attribute"

    @pytest.mark.parametrize("template", SERVING_TEMPLATES)
    def test_template_service_has_no_modules_field(self, template: str) -> None:
        """ServiceConfig.modules was removed in 0.6.2; configs must not include it."""
        svc = self._get_service_config(str(ROOT / "templates" / template / "pyproject.toml"))
        if svc is not None:
            assert "modules" not in svc, f"templates/{template} has obsolete 'modules' field"
