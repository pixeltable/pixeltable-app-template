"""Shared constants and fixtures for starter kit tests."""

from __future__ import annotations

import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent

PATTERNS: list[str] = ["serving", "batch"]
EXAMPLES: list[str] = ["video-search", "chat-agent"]

EXPECTED_FILES: dict[str, list[str]] = {
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

REMOVED_PATHS: list[str] = [
    "templates",
    "backend",
    "frontend",
    "deploy",
    "batch/deploy",
]


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
