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
    """Export images to the requested format.

    Supported formats: "jpg", "png", "pdf".
    For PDF, all pages are combined into a single PDF file.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    fmt_l = fmt.lower()
    if fmt_l in {"jpg", "jpeg"}:
        suffix = ".jpg"
        pil_format = "JPEG"
        paths: list[str] = []
        for i, image in enumerate(images, start=1):
            path = out / f"{stem}_page_{i:03d}{suffix}"
            rgb = image.convert("RGB")
            rgb.save(
                path,
                format=pil_format,
                quality=quality,
                optimize=True,
                dpi=(200, 200),
            )
            paths.append(str(path))
        return paths
    elif fmt_l == "png":
        suffix = ".png"
        pil_format = "PNG"
        paths: list[str] = []
        for i, image in enumerate(images, start=1):
            path = out / f"{stem}_page_{i:03d}{suffix}"
            rgb = image.convert("RGB")
            rgb.save(path, format=pil_format, optimize=True)
            paths.append(str(path))
        return paths
    elif fmt_l == "pdf":
        # Combine all pages into a single PDF file.
        pdf_path = out / f"{stem}.pdf"
        # Ensure all images are RGB.
        rgb_images = [img.convert("RGB") for img in images]
        if not rgb_images:
            raise ValueError("No images to export as PDF")
        first, *rest = rgb_images
        first.save(
            pdf_path,
            format="PDF",
            save_all=True,
            append_images=rest,
        )
        return [str(pdf_path)]
    else:
        raise ValueError("fmt must be jpg, png, or pdf")


def write_manifest(path: str | Path, data: dict[str, Any]) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return str(target)
