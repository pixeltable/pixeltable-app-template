"""TOML configuration for the two apps."""

from __future__ import annotations

import tomllib

import pytest

from tests.conftest import APPS, ROOT


def _load_toml(path: str) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


class TestAppPyprojectToml:
    @pytest.mark.parametrize("app", APPS)
    def test_toml_parses(self, app: str) -> None:
        cfg = _load_toml(str(ROOT / app / "pyproject.toml"))
        assert "project" in cfg
        assert "name" in cfg["project"]

    @pytest.mark.parametrize("app", APPS)
    def test_requires_python(self, app: str) -> None:
        cfg = _load_toml(str(ROOT / app / "pyproject.toml"))
        assert cfg["project"].get("requires-python") == ">=3.11"

    @pytest.mark.parametrize("app", APPS)
    def test_pixeltable_minimum_version(self, app: str) -> None:
        cfg = _load_toml(str(ROOT / app / "pyproject.toml"))
        deps = cfg["project"].get("dependencies", [])
        pxt_deps = [d for d in deps if d.startswith("pixeltable")]
        assert any("pixeltable" in d and ">=0.7.4" in d for d in pxt_deps), (
            f"{app} must pin pixeltable[serve]>=0.7.4, got {pxt_deps}"
        )

    def test_chat_agent_anthropic_below_v1(self) -> None:
        cfg = _load_toml(str(ROOT / "chat-agent" / "pyproject.toml"))
        deps = cfg["project"].get("dependencies", [])
        assert any(d.startswith("anthropic") and "<1" in d for d in deps), (
            "pixeltable 0.7.4 talks to Anthropic via httpx; anthropic>=1 needs httpx2"
        )


class TestProjectRoot:
    @pytest.mark.parametrize("app", APPS)
    def test_app_has_pixeltable_toml(self, app: str) -> None:
        text = (ROOT / app / "pixeltable.toml").read_text(encoding="utf-8")
        assert "[[pixeltable.database]]" in text


class TestBuildSystem:
    @pytest.mark.parametrize("app", APPS)
    def test_app_has_build_system(self, app: str) -> None:
        cfg = _load_toml(str(ROOT / app / "pyproject.toml"))
        assert "build-system" in cfg
        setuptools = cfg.get("tool", {}).get("setuptools", {})
        assert "app" in setuptools.get("py-modules", [])


class TestNoTomlService:
    @pytest.mark.parametrize("app", APPS)
    def test_app_has_no_service_table(self, app: str) -> None:
        cfg = _load_toml(str(ROOT / app / "pyproject.toml"))
        services = cfg.get("tool", {}).get("pixeltable", {}).get("service")
        assert not services, f"{app} still has [tool.pixeltable.service]"
