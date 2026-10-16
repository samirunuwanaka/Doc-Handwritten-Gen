"""High-resolution image export and job manifest."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image


def export_images(
    images: list[Image.Image],
    out_dir: str | Path,
    stem: str,
    fmt: str = "jpg",
    quality: int = 92,
) -> list[str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    fmt_l = fmt.lower()
    if fmt_l in {"jpg", "jpeg"}:
        suffix = ".jpg"
        pil_format = "JPEG"
    elif fmt_l == "png":
        suffix = ".png"
        pil_format = "PNG"
    else:
        raise ValueError("fmt must be jpg or png")

    for i, image in enumerate(images, start=1):
        path = out / f"{stem}_page_{i:03d}{suffix}"
        rgb = image.convert("RGB")
        if pil_format == "JPEG":
            rgb.save(path, format=pil_format, quality=quality, optimize=True, dpi=(200, 200))
        else:
            rgb.save(path, format=pil_format, optimize=True)
        paths.append(str(path))
    return paths


def write_manifest(path: str | Path, data: dict[str, Any]) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return str(target)
