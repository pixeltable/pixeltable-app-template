"""Shared constants and fixtures for starter kit tests."""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

PATTERNS: list[str] = ["backend", "serving", "batch"]

TEMPLATES: list[str] = [
    "agent",
    "audio-intel",
    "content-pipeline",
    "data-lab",
    "full-stack-showcase",
    "multimodal-rag",
    "video-intel",
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
    "agent": ["schema.py", "pyproject.toml", "app.py"],
    "audio-intel": ["schema.py", "pyproject.toml", "app.py", "functions.py"],
    "content-pipeline": ["schema.py", "pyproject.toml", "pipeline.py", "functions.py"],
    "data-lab": ["schema.py", "pyproject.toml", "export.py"],
    "full-stack-showcase": ["schema.py", "pyproject.toml", "app.py", "functions.py", "config.py", "models.py"],
    "multimodal-rag": ["schema.py", "pyproject.toml", "app.py", "functions.py"],
    "video-intel": ["schema.py", "pyproject.toml", "functions.py"],
}
