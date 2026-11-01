"""Shared paths for the offline tests."""

from pathlib import Path

import pytest

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@pytest.fixture(autouse=True)
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """These tests must not call a model, even if a key is sitting in the environment."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
