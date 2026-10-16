"""Reusable handwriting style profiles — one identity per document job."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).resolve().parents[3]
_PROFILES_PATH = _ROOT / "configs" / "profiles.yaml"


@dataclass(frozen=True)
class HandwritingProfile:
    name: str
    display_name: str
    base_stroke_width: float
    ink_color: tuple[int, int, int]
    ink_opacity: float
    slant_degrees: float
    char_spacing: float
    word_spacing: float
    relative_size: float
    curvature: float
    baseline_drift: float
    line_drift: float
    variation: float
    synthesis_level: str = "C"

    def to_manifest(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "synthesis_level": self.synthesis_level,
            "ink_color": list(self.ink_color),
            "slant_degrees": self.slant_degrees,
            "note": "Level C = script-aware glyph fallback with controlled variation",
        }


def _load_raw() -> dict[str, Any]:
    if not _PROFILES_PATH.is_file():
        raise FileNotFoundError(f"Missing profiles config: {_PROFILES_PATH}")
    data = yaml.safe_load(_PROFILES_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("profiles.yaml must be a mapping")
    return data


def list_profiles() -> list[str]:
    return sorted(_load_raw())


def load_profile(name: str) -> HandwritingProfile:
    raw = _load_raw()
    if name not in raw:
        known = ", ".join(sorted(raw))
        raise KeyError(f"Unknown profile '{name}'. Known: {known}")
    item = raw[name]
    color = item.get("ink_color", [20, 28, 48])
    return HandwritingProfile(
        name=name,
        display_name=item.get("display_name", name),
        base_stroke_width=float(item.get("base_stroke_width", 1.8)),
        ink_color=(int(color[0]), int(color[1]), int(color[2])),
        ink_opacity=float(item.get("ink_opacity", 0.9)),
        slant_degrees=float(item.get("slant_degrees", 5.0)),
        char_spacing=float(item.get("char_spacing", 1.05)),
        word_spacing=float(item.get("word_spacing", 1.2)),
        relative_size=float(item.get("relative_size", 1.0)),
        curvature=float(item.get("curvature", 0.25)),
        baseline_drift=float(item.get("baseline_drift", 0.8)),
        line_drift=float(item.get("line_drift", 1.2)),
        variation=float(item.get("variation", 0.08)),
        synthesis_level=str(item.get("synthesis_level", "C")),
    )
