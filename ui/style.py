from pathlib import Path

from config import settings


def load_stylesheet() -> str:
    """Load QSS from assets. Return empty string if not found."""
    stylesheet_path: Path = settings.STYLESHEET_FILE
    if not stylesheet_path.exists():
        return ""
    return stylesheet_path.read_text(encoding="utf-8")
