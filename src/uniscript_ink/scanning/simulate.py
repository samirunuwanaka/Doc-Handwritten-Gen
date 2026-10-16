"""Subtle clean-scan simulation. Default is clean (no damage artefacts)."""

from __future__ import annotations

from PIL import Image, ImageEnhance, ImageFilter


def apply_scan(image: Image.Image, mode: str = "clean") -> Image.Image:
    if mode == "clean":
        return image
    if mode != "subtle":
        raise ValueError("scan mode must be 'clean' or 'subtle'")

    out = image.convert("RGB")
    # Mild softness and contrast — no dust, stains, tears, or heavy JPEG damage.
    out = out.filter(ImageFilter.GaussianBlur(radius=0.35))
    out = ImageEnhance.Contrast(out).enhance(1.04)
    out = ImageEnhance.Brightness(out).enhance(1.01)
    return out
