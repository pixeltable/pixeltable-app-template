"""Shared constants and fixtures for starter kit tests."""

from __future__ import annotations

import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent

PATTERNS: list[str] = ["backend", "serving", "batch"]

TEMPLATES: list[str] = [
    "audio-transcription",
    "chat-agent",
    "full-stack-showcase",
    "image-dataset",
    "knowledge-base",
    "media-indexing",
    "video-search",
]

# Templates that declare TableModel + FastAPIRouter in app.py (no schema.py).
APPLICATION_FILE_TEMPLATES: list[str] = [
    "image-dataset",
    "media-indexing",
    "video-search",
]

# UI templates that still apply via import schema / python app.py.
SCHEMA_TEMPLATES: list[str] = [
    "audio-transcription",
    "chat-agent",
    "full-stack-showcase",
    "knowledge-base",
]

EXPECTED_FILES: dict[str, list[str]] = {
    "backend": [
        "pyproject.toml",
        "pixeltable.toml",
        "main.py",
        "config.py",
        "models.py",
        "functions.py",
        "setup_pixeltable.py",
        "routers/data.py",
        "routers/search.py",
        "routers/agent.py",
    ],
    "serving": [
        "pyproject.toml",
        "pixeltable.toml",
        "app.py",
        "Dockerfile",
        "docker-compose.yml",
    ],
    "batch": [
        "pyproject.toml",
        "pixeltable.toml",
        "app.py",
        "pipeline.py",
        "sample_batch.json",
        "Dockerfile",
        "docker-compose.yml",
    ],
}

EXPECTED_TEMPLATE_FILES: dict[str, list[str]] = {
    "audio-transcription": ["schema.py", "pyproject.toml", "pixeltable.toml", "app.py", "functions.py"],
    "chat-agent": ["schema.py", "pyproject.toml", "pixeltable.toml", "app.py"],
    "full-stack-showcase": ["schema.py", "pyproject.toml", "pixeltable.toml", "app.py", "config.py", "functions.py"],
    "image-dataset": ["app.py", "pyproject.toml", "pixeltable.toml", "export.py"],
    "knowledge-base": ["schema.py", "pyproject.toml", "pixeltable.toml", "app.py", "functions.py"],
    "media-indexing": ["app.py", "pyproject.toml", "pixeltable.toml", "pipeline.py", "functions.py"],
    "video-search": ["app.py", "pyproject.toml", "pixeltable.toml", "functions.py"],
}


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run slow schema import smoke tests (needs Pixeltable + model downloads)",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "slow: schema import smoke tests requiring Pixeltable")


def pytest_runtest_setup(item: pytest.Item) -> None:
    if item.get_closest_marker("slow") and not item.config.getoption("--run-slow"):
        pytest.skip("Slow test: pass --run-slow to enable.")
