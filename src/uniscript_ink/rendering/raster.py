"""Raster rendering for Level C glyph handwriting fallback."""

from __future__ import annotations

import hashlib
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from uniscript_ink.handwriting.profiles import HandwritingProfile
from uniscript_ink.ir import Document, WarningItem
from uniscript_ink.layout.paginate import PageSpec


def _seed_for(doc: Document, profile: HandwritingProfile) -> int:
    key = f"{doc.source_path}|{profile.name}|{doc.title or ''}"
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16)


def _draw_paper(draw: ImageDraw.ImageDraw, page: PageSpec) -> None:
    paper = page.paper
    bg = tuple(paper.get("background", [252, 252, 248]))
    draw.rectangle([0, 0, page.width, page.height], fill=bg)
    line_color = paper.get("line_color")
    spacing_pt = paper.get("line_spacing_pt")
    if line_color and spacing_pt:
        # estimate dpi from page height ~ A4
        dpi = page.height / 11.69
        spacing = float(spacing_pt) * dpi / 72.0
        margin = float(paper.get("margin_pt", 54)) * dpi / 72.0
        y = margin
        color = tuple(line_color)
        grid = bool(paper.get("grid"))
        while y < page.height - margin * 0.5:
            draw.line([(margin * 0.4, y), (page.width - margin * 0.4, y)], fill=color, width=1)
            y += spacing
        if grid:
            x = margin * 0.4
            while x < page.width - margin * 0.4:
                draw.line([(x, margin * 0.5), (x, page.height - margin * 0.5)], fill=color, width=1)
                x += spacing
    margin_line = paper.get("margin_line_color")
    if margin_line:
        dpi = page.height / 11.69
        margin = float(paper.get("margin_pt", 54)) * dpi / 72.0
        x = margin * 0.75
        draw.line([(x, margin * 0.4), (x, page.height - margin * 0.4)], fill=tuple(margin_line), width=2)


def _ink_rgba(profile: HandwritingProfile) -> tuple[int, int, int, int]:
    r, g, b = profile.ink_color
    a = max(0, min(255, int(profile.ink_opacity * 255)))
    return (r, g, b, a)


def render_pages(
    doc: Document,
    pages: list[PageSpec],
    profile: HandwritingProfile,
    font_path: str,
) -> list[Image.Image]:
    """Render pages using Level C glyph fallback with controlled variation."""
    rng = random.Random(_seed_for(doc, profile))
    images: list[Image.Image] = []
    missing_glyphs: set[str] = set()
    slant = math.radians(profile.slant_degrees)

    for page in pages:
        base = Image.new("RGB", (page.width, page.height), tuple(page.paper.get("background", [252, 252, 248])))
        draw = ImageDraw.Draw(base)
        _draw_paper(draw, page)

        # Draw text on RGBA overlay so opacity works.
        overlay = Image.new("RGBA", (page.width, page.height), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        ink = _ink_rgba(profile)

        for line in page.lines:
            font = ImageFont.truetype(font_path, line.font_size)
            x = line.x
            y = line.y + rng.uniform(-line.baseline_jitter, line.baseline_jitter)
            for ch in line.text:
                if ch == " ":
                    # word spacing
                    space = font.getlength(" ") * profile.word_spacing
                    x += space
                    continue
                # Glyph coverage check
                try:
                    glyph_w = font.getlength(ch)
                except Exception:
                    glyph_w = font.getlength("?")
                bbox = font.getbbox(ch)
                # Pillow may still draw .notdef; detect empty-ish advance for some fonts
                if bbox is None or (bbox[2] - bbox[0] == 0 and ch.strip()):
                    missing_glyphs.add(ch)
                    continue

                dx = rng.uniform(-profile.variation, profile.variation) * line.font_size
                dy = rng.uniform(-profile.variation, profile.variation) * line.font_size
                # Mild slant via horizontal shear offset by vertical position within line
                shear = math.tan(slant) * (dy * 0.2)
                cx = x + dx + shear
                cy = y + dy
                odraw.text((cx, cy), ch, font=font, fill=ink)
                x += glyph_w * profile.char_spacing

        composed = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
        images.append(composed)

    if missing_glyphs:
        sample = "".join(sorted(missing_glyphs)[:20])
        doc.warnings.append(
            WarningItem(
                code="missing_glyphs",
                message=f"Skipped {len(missing_glyphs)} distinct characters lacking glyph metrics.",
                context=sample,
                severity="warning",
            )
        )

    doc.meta["synthesis_level"] = profile.synthesis_level
    doc.meta["font_path"] = str(Path(font_path).name)
    return images
