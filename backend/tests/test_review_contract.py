"""Locks the bits a reviewer hits on a clean clone: port, Gemini request, no secrets."""

import json
from pathlib import Path

from app.constants import LOCAL_API_PORT
from app.pipeline.gemini import generation_config, text_from_generate_response

ROOT = Path(__file__).resolve().parents[2]
_SKIP_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "var",
    "logs",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}
_TEXT_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".md",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".sql",
    ".css",
    ".html",
    ".example",
    ".svg",
}


def test_readme_and_vite_share_the_api_port() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    vite = (ROOT / "frontend" / "vite.config.ts").read_text(encoding="utf-8")
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    port = str(LOCAL_API_PORT)
    assert f"--port {port}" in readme
    assert f"127.0.0.1:{port}" in readme
    assert f"127.0.0.1:{port}" in vite
    assert f"127.0.0.1:{port}" in example
    assert "8010" not in readme
    assert "8010" not in vite
    assert "8010" not in example


def test_gemini_38_request_omits_temperature_and_uses_low_thinking() -> None:
    config = generation_config()
    assert "temperature" not in config
    assert "topP" not in config
    assert "topK" not in config
    assert config["responseMimeType"] == "application/json"
    assert config["thinkingConfig"] == {"thinkingLevel": "low"}


def test_gemini_answer_skips_the_thought_part() -> None:
    payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"thought": True, "text": "ignore this"},
                        {"text": '{"language":"en"}'},
                    ]
                }
            }
        ]
    }
    assert text_from_generate_response(payload) == '{"language":"en"}'


def test_gemini_garbage_response_is_rejected() -> None:
    try:
        text_from_generate_response({"error": {"message": "nope"}})
    except json.JSONDecodeError:
        return
    raise AssertionError("garbage model payload must not look like an answer")


def test_tree_has_no_live_secrets() -> None:
    """File paths only. A hit must not print the secret itself."""
    token_prefix = "github" + "_pat_"
    key_prefix = "AI" + "za"
    hits: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if path.name == ".env" or path.suffix.lower() not in _TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if token_prefix in text or _looks_like_live_key(text, key_prefix):
            hits.append(str(path.relative_to(ROOT)))
    assert hits == []


def _looks_like_live_key(text: str, key_prefix: str) -> bool:
    start = 0
    while True:
        found = text.find(key_prefix, start)
        if found < 0:
            return False
        tail = text[found + len(key_prefix) : found + len(key_prefix) + 20]
        if len(tail) >= 20 and tail.isalnum():
            return True
        start = found + len(key_prefix)
