"""TOML configuration for the two apps."""

from __future__ import annotations

import re
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

    @staticmethod
    def _declared_floor(app: str) -> str:
        cfg = _load_toml(str(ROOT / app / "pyproject.toml"))
        deps = cfg["project"].get("dependencies", [])
        pxt = [d for d in deps if d.startswith("pixeltable")]
        assert len(pxt) == 1, f"{app} must declare exactly one pixeltable dependency, got {pxt}"
        spec = pxt[0]
        assert ">=" in spec, f"{app} must declare a pixeltable floor, got {spec!r}"
        return spec.split(">=", 1)[1].strip().strip('"')

    @staticmethod
    def _locked_version(app: str) -> str:
        """The pixeltable version resolved in that app's uv.lock."""
        text = (ROOT / app / "uv.lock").read_text(encoding="utf-8")
        m = re.search(r'^name = "pixeltable"\nversion = "([^"]+)"', text, re.MULTILINE)
        assert m is not None, f"{app}/uv.lock does not pin a pixeltable version"
        return m.group(1)

    def test_both_apps_declare_the_same_floor(self) -> None:
        floors = {app: self._declared_floor(app) for app in APPS}
        assert len(set(floors.values())) == 1, f"apps disagree on the pixeltable floor: {floors}"

    @pytest.mark.parametrize("app", APPS)
    def test_floor_matches_lockfile(self, app: str) -> None:
        """The floor is a compatibility claim; the lock is what ships (Dockerfiles use --frozen).

        Asserting they agree means a relock without a floor bump -- or the reverse -- fails here
        rather than silently shipping a README that says one thing and an image that does another.
        """
        floor, locked = self._declared_floor(app), self._locked_version(app)
        assert floor == locked, (
            f"{app}: pyproject floor >={floor} but uv.lock pins {locked}; bump the floor and re-run `uv lock` together"
        )

    def test_chat_agent_anthropic_below_v1(self) -> None:
        cfg = _load_toml(str(ROOT / "chat-agent" / "pyproject.toml"))
        deps = cfg["project"].get("dependencies", [])
        assert any(d.startswith("anthropic") and "<1" in d for d in deps), (
            "anthropic<1 caps httpx<1, which is what holds the lock at httpx 0.28.x; "
            "pixeltable only declares httpx>=0.27, so dropping this cap moves httpx "
            "and the failure lands at request time, not install time"
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
