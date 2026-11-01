"""Read approved marketing files from the data pack."""

from pathlib import Path

_BRAND_MAX = 16_000


def read_brand_context(data_dir: Path) -> str:
    """Full brand_context.md for the writer and the learning job."""
    path = data_dir / "brand_context.md"
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8").strip()
    if len(text) <= _BRAND_MAX:
        return text
    return text[: _BRAND_MAX - 20] + "\n\n[truncated]"
