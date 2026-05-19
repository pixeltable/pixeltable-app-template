"""Schema import smoke tests.

These tests require Pixeltable (embedded Postgres) and download embedding models.
They are marked `slow` and skipped in fast CI runs. Run with:

    uv run pytest tests/test_schema.py -v --run-slow

To run in the serving venv (which has pixeltable installed):

    cd serving && uv run pytest ../tests/test_schema.py -v --run-slow
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from tests.conftest import ROOT

slow = pytest.mark.skipif(
    "--run-slow" not in sys.argv,
    reason="Slow test: needs Pixeltable + model downloads. Pass --run-slow to enable.",
)


@slow
class TestServingSchemaImport:
    """Verify serving/schema.py imports and creates tables in a temp Pixeltable home."""

    def test_schema_imports_cleanly(self, tmp_path: pytest.TempPathFactory) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import schema; print('OK')",
            ],
            cwd=str(ROOT / "serving"),
            env={**os.environ, "PIXELTABLE_HOME": str(tmp_path)},
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, f"schema import failed:\n{result.stderr}"
        assert "OK" in result.stdout


@slow
class TestBatchSchemaImport:
    """Verify batch/schema.py imports cleanly."""

    def test_schema_imports_cleanly(self, tmp_path: pytest.TempPathFactory) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import schema; print('OK')",
            ],
            cwd=str(ROOT / "batch"),
            env={**os.environ, "PIXELTABLE_HOME": str(tmp_path)},
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, f"schema import failed:\n{result.stderr}"
        assert "OK" in result.stdout
