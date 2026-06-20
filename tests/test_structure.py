"""Test that all patterns and templates have the expected file structure."""

from __future__ import annotations

import ast

import pytest

from tests.conftest import (
    EXPECTED_FILES,
    EXPECTED_TEMPLATE_FILES,
    PATTERNS,
    ROOT,
    TEMPLATES,
)

_DEPRECATED_PATTERNS: list[tuple[str, str]] = [
    ("FrameIterator", "Use frame_iterator from pixeltable.functions.video"),
    ("openai.vision", "Use openai.chat_completions with image_url content blocks"),
    ("from pixeltable.iterators import", "Use pixeltable.functions.* iterators instead"),
    (".add_index(", "Use add_embedding_index()"),
]


class TestPatternFiles:
    """Each deployment pattern ships the expected files."""

    @pytest.mark.parametrize("pattern", PATTERNS)
    def test_pattern_directory_exists(self, pattern: str) -> None:
        assert (ROOT / pattern).is_dir(), f"{pattern}/ directory missing"

    @pytest.mark.parametrize("pattern", PATTERNS)
    def test_expected_files_exist(self, pattern: str) -> None:
        for relpath in EXPECTED_FILES[pattern]:
            fpath = ROOT / pattern / relpath
            assert fpath.is_file(), f"{pattern}/{relpath} missing"

    @pytest.mark.parametrize("pattern", PATTERNS)
    def test_pyproject_toml_exists(self, pattern: str) -> None:
        assert (ROOT / pattern / "pyproject.toml").is_file()

    @pytest.mark.parametrize("pattern", PATTERNS)
    def test_uv_lock_exists(self, pattern: str) -> None:
        assert (ROOT / pattern / "uv.lock").is_file(), f"{pattern}/uv.lock missing"


class TestTemplateFiles:
    """Each application template ships the expected files."""

    @pytest.mark.parametrize("template", TEMPLATES)
    def test_template_directory_exists(self, template: str) -> None:
        assert (ROOT / "templates" / template).is_dir(), f"templates/{template}/ missing"

    @pytest.mark.parametrize("template", TEMPLATES)
    def test_expected_files_exist(self, template: str) -> None:
        for relpath in EXPECTED_TEMPLATE_FILES[template]:
            fpath = ROOT / "templates" / template / relpath
            assert fpath.is_file(), f"templates/{template}/{relpath} missing"


class TestPythonSyntax:
    """All Python files parse without syntax errors."""

    @pytest.mark.parametrize("pattern", PATTERNS)
    def test_pattern_python_files_parse(self, pattern: str) -> None:
        for py_file in (ROOT / pattern).rglob("*.py"):
            if ".venv" in py_file.parts:
                continue
            source = py_file.read_text(encoding="utf-8")
            try:
                ast.parse(source, filename=str(py_file))
            except SyntaxError as exc:
                pytest.fail(f"Syntax error in {py_file.relative_to(ROOT)}: {exc}")

    @pytest.mark.parametrize("template", TEMPLATES)
    def test_template_python_files_parse(self, template: str) -> None:
        for py_file in (ROOT / "templates" / template).rglob("*.py"):
            if ".venv" in py_file.parts:
                continue
            source = py_file.read_text(encoding="utf-8")
            try:
                ast.parse(source, filename=str(py_file))
            except SyntaxError as exc:
                pytest.fail(f"Syntax error in {py_file.relative_to(ROOT)}: {exc}")


class TestDocumentation:
    """Key documentation files exist."""

    @pytest.mark.parametrize(
        "relpath",
        ["README.md", "AGENTS.md", ".env.example", "Dockerfile", "docker-compose.yml"],
    )
    def test_root_docs_exist(self, relpath: str) -> None:
        assert (ROOT / relpath).is_file(), f"{relpath} missing from repo root"

    @pytest.mark.parametrize("pattern", ["serving", "batch"])
    def test_pattern_has_readme(self, pattern: str) -> None:
        assert (ROOT / pattern / "README.md").is_file(), f"{pattern}/README.md missing"

    @pytest.mark.parametrize("template", TEMPLATES)
    def test_template_has_readme(self, template: str) -> None:
        assert (ROOT / "templates" / template / "README.md").is_file(), f"templates/{template}/README.md missing"


class TestNoAntiPatterns:
    """Guard against known anti-patterns we've already fixed."""

    _BANNED_ENV_VAR = "PYTHON" + "PATH"

    def test_no_banned_env_var_references(self) -> None:
        """Env-var hack was removed; make sure it doesn't creep back."""
        hits: list[str] = []
        skip = {".venv", ".git", "node_modules", "tests"}
        for ext in ("*.py", "*.toml", "*.yml", "*.yaml", "*.md"):
            for f in ROOT.rglob(ext):
                if skip & set(f.parts):
                    continue
                text = f.read_text(encoding="utf-8", errors="ignore")
                if self._BANNED_ENV_VAR in text:
                    hits.append(str(f.relative_to(ROOT)))
        assert hits == [], f"{self._BANNED_ENV_VAR} found in: {hits}"

    def test_no_deprecated_pixeltable_apis(self) -> None:
        """Ban known-deprecated Pixeltable APIs from production code."""
        hits: list[str] = []
        skip = {".venv", ".git", "node_modules", "tests", "prototype"}
        scan_roots = [
            ROOT / "backend",
            ROOT / "batch",
            ROOT / "serving",
            ROOT / "templates",
        ]
        for root in scan_roots:
            for py_file in root.rglob("*.py"):
                if skip & set(py_file.parts):
                    continue
                text = py_file.read_text(encoding="utf-8", errors="ignore")
                for pattern, _ in _DEPRECATED_PATTERNS:
                    if pattern in text:
                        hits.append(f"{py_file.relative_to(ROOT)}: {pattern}")
        assert hits == [], "Deprecated Pixeltable APIs found:\n" + "\n".join(hits)
