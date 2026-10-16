"""Font resolution for Level C glyph fallback."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from uniscript_ink.ir import WarningItem

# Prefer handwriting-like fonts when present; fall back to readable Unicode fonts.
_CANDIDATES_WINDOWS = [
    r"C:\Windows\Fonts\segoesc.ttf",  # Segoe Script
    r"C:\Windows\Fonts\segoepr.ttf",  # Segoe Print
    r"C:\Windows\Fonts\comic.ttf",
    r"C:\Windows\Fonts\calibri.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\malgun.ttf",  # Korean
    r"C:\Windows\Fonts\Nirmala.ttf",  # Indic
    r"C:\Windows\Fonts\mmrtext.ttf",  # Myanmar / broader
    r"C:\Windows\Fonts\msyi.ttf",
    r"C:\Windows\Fonts\seguiemj.ttf",
]

_CANDIDATES_UNIX = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/System/Library/Fonts/Supplemental/Comic Sans MS.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
]


@lru_cache(maxsize=1)
def resolve_font_path() -> str:
    env = os.environ.get("UNISCRIPT_INK_FONT")
    if env and Path(env).is_file():
        return env

    candidates = _CANDIDATES_WINDOWS if os.name == "nt" else _CANDIDATES_UNIX
    # Also try Windows list on non-Windows if paths somehow exist (WSL).
    for path in candidates + _CANDIDATES_WINDOWS + _CANDIDATES_UNIX:
        if Path(path).is_file():
            return path
    raise FileNotFoundError(
        "No usable TrueType font found. Set UNISCRIPT_INK_FONT to a .ttf path."
    )


def font_warning_if_needed(font_path: str) -> WarningItem | None:
    name = Path(font_path).name.lower()
    handwriting_like = any(token in name for token in ("script", "hand", "comic", "segoepr"))
    if not handwriting_like:
        return WarningItem(
            code="font_not_handwriting_labelled",
            message=(
                f"Using font '{Path(font_path).name}' for Level C glyph fallback. "
                "It may not look handwritten for all scripts."
            ),
            context=font_path,
        )
    return None
