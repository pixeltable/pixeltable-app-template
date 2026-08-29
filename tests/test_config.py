"""TOML configuration for serving and batch."""

from __future__ import annotations

import tomllib

import pytest

from tests.conftest import EXAMPLES, PATTERNS, ROOT


def _load_toml(path: str) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


class TestPatternPyprojectToml:
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
    def test_pixeltable_minimum_version(self, pattern: str) -> None:
        cfg = _load_toml(str(ROOT / pattern / "pyproject.toml"))
        deps = cfg["project"].get("dependencies", [])
        pxt_deps = [d for d in deps if d.startswith("pixeltable")]
        assert any(">=0.6.5" in d for d in pxt_deps), f"{pattern} must require pixeltable>=0.6.5, got {pxt_deps}"


class TestProjectRoot:
    @pytest.mark.parametrize("pattern", PATTERNS)
    def test_pattern_has_pixeltable_toml(self, pattern: str) -> None:
        text = (ROOT / pattern / "pixeltable.toml").read_text(encoding="utf-8")
        assert "[[pixeltable.database]]" in text


class TestServingBuildSystem:
    def test_serving_has_build_system(self) -> None:
        cfg = _load_toml(str(ROOT / "serving" / "pyproject.toml"))
        assert "build-system" in cfg
        setuptools = cfg.get("tool", {}).get("setuptools", {})
        assert "app" in setuptools.get("py-modules", [])


class TestNoTomlService:
    @pytest.mark.parametrize("pattern", PATTERNS)
    def test_pattern_has_no_service_table(self, pattern: str) -> None:
        cfg = _load_toml(str(ROOT / pattern / "pyproject.toml"))
        services = cfg.get("tool", {}).get("pixeltable", {}).get("service")
        assert not services, f"{pattern} still has [tool.pixeltable.service]"


class TestExampleToml:
    @pytest.mark.parametrize("example", EXAMPLES)
    def test_example_toml_parses(self, example: str) -> None:
        cfg = _load_toml(str(ROOT / "examples" / example / "pyproject.toml"))
        assert "project" in cfg
        deps = cfg["project"].get("dependencies", [])
        pxt_deps = [d for d in deps if d.startswith("pixeltable")]
        assert any(">=0.6.5" in d for d in pxt_deps), f"{example} must require pixeltable>=0.6.5"
        services = cfg.get("tool", {}).get("pixeltable", {}).get("service")
        assert not services, f"examples/{example} still has [tool.pixeltable.service]"
        text = (ROOT / "examples" / example / "pixeltable.toml").read_text(encoding="utf-8")
        assert "[[pixeltable.database]]" in text
        setuptools = cfg.get("tool", {}).get("setuptools", {})
        assert "app" in setuptools.get("py-modules", [])
