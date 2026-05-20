"""Shared constants and fixtures for starter kit tests."""

from __future__ import annotations

import pathlib

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

EXPECTED_FILES: dict[str, list[str]] = {
    "backend": [
        "pyproject.toml",
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
        "schema.py",
        "Dockerfile",
        "docker-compose.yml",
    ],
    "batch": [
        "pyproject.toml",
        "schema.py",
        "pipeline.py",
        "sample_batch.json",
        "Dockerfile",
        "docker-compose.yml",
    ],
}

EXPECTED_TEMPLATE_FILES: dict[str, list[str]] = {
    "audio-transcription": ["schema.py", "pyproject.toml", "app.py", "functions.py"],
    "chat-agent": ["schema.py", "pyproject.toml", "app.py"],
    "full-stack-showcase": ["schema.py", "pyproject.toml", "app.py", "config.py", "functions.py"],
    "image-dataset": ["schema.py", "pyproject.toml", "export.py"],
    "knowledge-base": ["schema.py", "pyproject.toml", "app.py", "functions.py"],
    "media-indexing": ["schema.py", "pyproject.toml", "pipeline.py", "functions.py"],
    "video-search": ["schema.py", "pyproject.toml", "functions.py"],
}
