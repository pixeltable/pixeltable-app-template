"""Advertised apps have the expected file structure."""

from __future__ import annotations

import ast
import json
import pathlib
import re

import pytest

from tests.conftest import EXPECTED_FILES, PATTERNS, REMOVED_PATHS, ROOT

_DEPRECATED_PATTERNS: list[tuple[str, str]] = [
    ("FrameIterator", "Use frame_iterator from pixeltable.functions.video"),
    ("openai.vision", "Use openai.chat_completions with image_url content blocks"),
    ("from pixeltable.iterators import", "Use pixeltable.functions.* iterators instead"),
    (".add_index(", "Use EmbeddingIndex on the model"),
]

_BANNED_APPLY: tuple[str, ...] = (
    "pxt serve",
    "[[tool.pixeltable.service]]",
    "tool.pixeltable.service",
    "python schema.py",
    "pxt schema update schema.py",
    "pxt.create_table",
    "setup_pixeltable",
    "add_embedding_index",
    "pxt db create",
    "add_computed_column",
    "declarative multimodal data infrastructure",
)

_PXT_SERVE_RE = re.compile(r"pxt serve(?!ice)")
_HOSTED_SERVICE_RUN_RE = re.compile(r"pxt service run[^\n]*pxt://")
_HOSTED_SERVICE_UPDATE = "pxt service update app.py pxt://"

_CONTRACT_MD_FILES: tuple[str, ...] = ("README.md", "AGENTS.md", "CONTRIBUTING.md")
_CONTRACT_MD_DIRS: tuple[str, ...] = ("chat-agent", "video-search")


def _contract_markdown_files() -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    skip = {".venv", ".git", "node_modules", "tests"}
    for relpath in _CONTRACT_MD_FILES:
        path = ROOT / relpath
        if path.is_file():
            files.append(path)
    for dirname in _CONTRACT_MD_DIRS:
        folder = ROOT / dirname
        if not folder.is_dir():
            continue
        for path in folder.rglob("*.md"):
            if skip & set(path.parts):
                continue
            files.append(path)
    return files


def _banned_apply_present(text: str, token: str) -> bool:
    if token == "pxt serve":
        return _PXT_SERVE_RE.search(text) is not None
    return token in text


class TestPatternFiles:
    @pytest.mark.parametrize("pattern", PATTERNS)
    def test_pattern_directory_exists(self, pattern: str) -> None:
        assert (ROOT / pattern).is_dir(), f"{pattern}/ directory missing"

    @pytest.mark.parametrize("pattern", PATTERNS)
    def test_expected_files_exist(self, pattern: str) -> None:
        for relpath in EXPECTED_FILES[pattern]:
            fpath = ROOT / pattern / relpath
            assert fpath.is_file(), f"{pattern}/{relpath} missing"

    @pytest.mark.parametrize("pattern", PATTERNS)
    def test_uv_lock_exists(self, pattern: str) -> None:
        assert (ROOT / pattern / "uv.lock").is_file(), f"{pattern}/uv.lock missing"

    @pytest.mark.parametrize("relpath", REMOVED_PATHS)
    def test_removed_paths_absent(self, relpath: str) -> None:
        assert not (ROOT / relpath).exists(), f"{relpath} should not ship"


class TestPythonSyntax:
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


class TestDocumentation:
    @pytest.mark.parametrize(
        "relpath",
        ["README.md", "AGENTS.md", ".env.example"],
    )
    def test_root_docs_exist(self, relpath: str) -> None:
        assert (ROOT / relpath).is_file(), f"{relpath} missing from repo root"

    @pytest.mark.parametrize("pattern", PATTERNS)
    def test_pattern_has_readme(self, pattern: str) -> None:
        assert (ROOT / pattern / "README.md").is_file(), f"{pattern}/README.md missing"


class TestApplicationFile:
    @pytest.mark.parametrize("pattern", PATTERNS)
    def test_app_is_tablemodel(self, pattern: str) -> None:
        source = (ROOT / pattern / "app.py").read_text(encoding="utf-8")
        assert "model_base()" in source
        assert "FastAPIRouter" in source
        assert "__indexes__" in source
        assert "add_embedding_index" not in source
        assert "pxt.create_table" not in source


class TestNoAntiPatterns:
    _BANNED_ENV_VAR = "PYTHON" + "PATH"

    def test_no_banned_env_var_references(self) -> None:
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

    @staticmethod
    def _is_pxt_query_decorator(node: ast.AST) -> bool:
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            return node.func.attr == "query" and isinstance(node.func.value, ast.Name) and node.func.value.id == "pxt"
        if isinstance(node, ast.Attribute):
            return node.attr == "query" and isinstance(node.value, ast.Name) and node.value.id == "pxt"
        return False

    def test_no_sim_alias_in_pxt_query(self) -> None:
        hits: list[str] = []
        skip = {".venv", ".git", "node_modules", "tests"}
        for folder in PATTERNS:
            for py_file in (ROOT / folder).rglob("*.py"):
                if skip & set(py_file.parts):
                    continue
                tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
                for node in ast.walk(tree):
                    if not isinstance(node, ast.FunctionDef):
                        continue
                    if not any(self._is_pxt_query_decorator(d) for d in node.decorator_list):
                        continue
                    for sub in ast.walk(node):
                        if (
                            isinstance(sub, ast.keyword)
                            and sub.arg == "sim"
                            and isinstance(sub.value, ast.Name)
                            and sub.value.id == "sim"
                        ):
                            hits.append(f"{py_file.relative_to(ROOT)}:{node.name}")
        assert hits == [], "sim=sim in @pxt.query found:\n" + "\n".join(hits)

    def test_no_deprecated_pixeltable_apis(self) -> None:
        hits: list[str] = []
        skip = {".venv", ".git", "node_modules", "tests"}
        for folder in PATTERNS:
            for py_file in (ROOT / folder).rglob("*.py"):
                if skip & set(py_file.parts):
                    continue
                text = py_file.read_text(encoding="utf-8", errors="ignore")
                for token, _ in _DEPRECATED_PATTERNS:
                    if token in text:
                        hits.append(f"{py_file.relative_to(ROOT)}: {token}")
        assert hits == [], "Deprecated Pixeltable APIs found:\n" + "\n".join(hits)

    def test_one_apply_path(self) -> None:
        hits: list[str] = []
        skip = {".venv", ".git", "node_modules", "tests"}
        scan_roots = [
            ROOT / "chat-agent",
            ROOT / "video-search",
            ROOT / "README.md",
            ROOT / "AGENTS.md",
            ROOT / "CONTRIBUTING.md",
        ]
        for root in scan_roots:
            paths = [root] if root.is_file() else list(root.rglob("*"))
            for f in paths:
                if not f.is_file() or skip & set(f.parts):
                    continue
                if f.suffix not in {".py", ".toml", ".md", ".yml", ".yaml"}:
                    continue
                text = f.read_text(encoding="utf-8", errors="ignore")
                for token in _BANNED_APPLY:
                    if _banned_apply_present(text, token):
                        hits.append(f"{f.relative_to(ROOT)}: {token}")
        assert hits == [], "Dead apply path found:\n" + "\n".join(hits)

    def test_no_hosted_pxt_service_run(self) -> None:
        hits: list[str] = []
        for f in _contract_markdown_files():
            text = f.read_text(encoding="utf-8", errors="ignore")
            for match in _HOSTED_SERVICE_RUN_RE.finditer(text):
                hits.append(f"{f.relative_to(ROOT)}: {match.group(0)}")
        assert hits == [], "pxt service run is local only:\n" + "\n".join(hits)

    def test_cloud_teaches_hosted_service_update(self) -> None:
        missing: list[str] = []
        for relpath in ("README.md", "AGENTS.md"):
            text = (ROOT / relpath).read_text(encoding="utf-8")
            if _HOSTED_SERVICE_UPDATE not in text:
                missing.append(relpath)
        assert missing == [], "Cloud copy must teach hosted pxt service update:\n" + "\n".join(missing)

    def test_no_em_dashes(self) -> None:
        hits: list[str] = []
        for f in _contract_markdown_files():
            if "\u2014" in f.read_text(encoding="utf-8", errors="ignore"):
                hits.append(str(f.relative_to(ROOT)))
        assert hits == [], f"U+2014 em dash found in: {hits}"


class TestGallery:
    def test_gallery_matches_paths(self) -> None:
        gallery_path = ROOT / "gallery.json"
        assert gallery_path.is_file()
        gallery = json.loads(gallery_path.read_text(encoding="utf-8"))
        recipes = gallery["recipes"]
        ids = {r["id"] for r in recipes}
        assert ids == set(PATTERNS)
        for recipe in recipes:
            github_path = ROOT / recipe["githubPath"]
            entry = github_path / recipe["entry"]
            assert entry.is_file(), f"{recipe['id']}: missing {entry.relative_to(ROOT)}"
            assert recipe["entry"] == "app.py"
            assert "scaffold" in recipe
            assert "--template" not in recipe["scaffold"]
            assert "--backend" not in recipe["scaffold"]
            assert "--batch" not in recipe["scaffold"]
            if recipe["id"] == "chat-agent":
                assert recipe["scaffold"] == "uvx pixeltable-new myapp"
            if recipe["id"] == "video-search":
                assert "--video" in recipe["scaffold"]
