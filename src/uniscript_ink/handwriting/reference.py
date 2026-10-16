"""Optional reference-handwriting style matching.

Analyzes a user-provided handwriting photo and derives a HandwritingProfile so
the whole document job uses one matched identity (ink, slant, weight, spacing).

Phase 1 matches visual style parameters (Level C). Exact character-shape cloning
from a photo requires Level B stroke / few-shot models and is reported as planned.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, ImageStat

from uniscript_ink.handwriting.profiles import HandwritingProfile, load_profile
from uniscript_ink.ir import WarningItem

_MAX_ANALYSIS_SIDE = 900
_SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


@dataclass
class ReferenceAnalysis:
    """Metrics extracted from a reference handwriting image."""

    source_path: str
    ink_color: tuple[int, int, int]
    ink_opacity: float
    slant_degrees: float
    stroke_width: float
    char_spacing: float
    word_spacing: float
    relative_size: float
    variation: float
    baseline_drift: float
    line_drift: float
    curvature: float
    ink_ratio: float
    confidence: float
    paper_color: tuple[int, int, int]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "ink_color": list(self.ink_color),
            "ink_opacity": round(self.ink_opacity, 3),
            "slant_degrees": round(self.slant_degrees, 2),
            "stroke_width": round(self.stroke_width, 2),
            "char_spacing": round(self.char_spacing, 3),
            "word_spacing": round(self.word_spacing, 3),
            "relative_size": round(self.relative_size, 3),
            "variation": round(self.variation, 3),
            "baseline_drift": round(self.baseline_drift, 2),
            "line_drift": round(self.line_drift, 2),
            "curvature": round(self.curvature, 3),
            "ink_ratio": round(self.ink_ratio, 4),
            "confidence": round(self.confidence, 3),
            "paper_color": list(self.paper_color),
            "notes": list(self.notes),
            "match_mode": "visual_identity_level_C",
            "exact_glyph_cloning": False,
        }


def _luma(r: int, g: int, b: int) -> float:
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _resize_for_analysis(image: Image.Image) -> Image.Image:
    w, h = image.size
    side = max(w, h)
    if side <= _MAX_ANALYSIS_SIDE:
        return image
    scale = _MAX_ANALYSIS_SIDE / side
    return image.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)


def _sample_pixels(rgb: Image.Image, step: int = 2) -> list[tuple[int, int, int, int, int]]:
    """Return (x, y, r, g, b) samples."""
    pixels = rgb.load()
    w, h = rgb.size
    out: list[tuple[int, int, int, int, int]] = []
    for y in range(0, h, step):
        for x in range(0, w, step):
            r, g, b = pixels[x, y][:3]
            out.append((x, y, r, g, b))
    return out


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return ordered[idx]


def _estimate_slant(ink_points: list[tuple[int, int]]) -> float:
    """Estimate writing slant in degrees from ink coordinates (PCA / covariance)."""
    if len(ink_points) < 40:
        return 5.0
    # Subsample for speed
    step = max(1, len(ink_points) // 2500)
    pts = ink_points[::step]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    mean_x = statistics.fmean(xs)
    mean_y = statistics.fmean(ys)
    sxx = syy = sxy = 0.0
    for x, y in pts:
        dx = x - mean_x
        dy = y - mean_y
        sxx += dx * dx
        syy += dy * dy
        sxy += dx * dy
    n = float(len(pts))
    sxx /= n
    syy /= n
    sxy /= n
    # Principal axis angle
    angle = 0.5 * math.atan2(2 * sxy, (sxx - syy) + 1e-9)
    degrees = math.degrees(angle)
    # Handwriting slant is usually modest; clamp to readable range
    # Vertical strokes dominate → near 0; convert residual toward pen slant heuristic
    if abs(degrees) > 45:
        degrees = degrees - 90 if degrees > 0 else degrees + 90
    return max(-18.0, min(18.0, degrees * -1.0))


def _estimate_stroke_width(mask: list[list[bool]], ink_points: list[tuple[int, int]]) -> float:
    """Approximate stroke thickness via local clear-radius sampling on a boolean mask."""
    if not ink_points:
        return 1.8
    h = len(mask)
    w = len(mask[0]) if h else 0
    radii: list[float] = []
    step = max(1, len(ink_points) // 400)
    max_r = 8
    for x, y in ink_points[::step]:
        found = None
        for r in range(1, max_r + 1):
            clear = True
            for dy in range(-r, r + 1):
                yy = y + dy
                if yy < 0 or yy >= h:
                    continue
                for dx in range(-r, r + 1):
                    if dx * dx + dy * dy > r * r:
                        continue
                    xx = x + dx
                    if xx < 0 or xx >= w:
                        continue
                    if not mask[yy][xx]:
                        clear = False
                        break
                if not clear:
                    break
            if not clear:
                found = float(r)
                break
        if found is not None:
            radii.append(found)
    if not radii:
        return 1.8
    # Map pixel radius to profile stroke width scale (~1.0–3.0)
    med = statistics.median(radii)
    return max(1.0, min(3.2, 0.7 + med * 0.45))


def analyze_reference_image(path: str | Path) -> ReferenceAnalysis:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Reference image not found: {source}")
    if source.suffix.lower() not in _SUPPORTED:
        raise ValueError(
            f"Unsupported reference format '{source.suffix}'. "
            f"Use one of: {', '.join(sorted(_SUPPORTED))}"
        )

    image = Image.open(source)
    image = ImageOps.exif_transpose(image).convert("RGB")
    image = _resize_for_analysis(image)
    samples = _sample_pixels(image, step=2)
    if len(samples) < 50:
        raise ValueError("Reference image is too small to analyze.")

    luminances = [_luma(r, g, b) for _, _, r, g, b in samples]
    paper_cut = _percentile(luminances, 85)
    # Ink is darker than paper
    ink_threshold = paper_cut - 28.0
    ink_samples = [(x, y, r, g, b) for x, y, r, g, b in samples if _luma(r, g, b) < ink_threshold]
    paper_samples = [(r, g, b) for _, _, r, g, b in samples if _luma(r, g, b) >= paper_cut - 5]

    notes: list[str] = []
    if len(ink_samples) < 30:
        notes.append("Low ink contrast detected; style confidence reduced.")
        # Fall back to darker quartile as ink
        dark_cut = _percentile(luminances, 25)
        ink_samples = [(x, y, r, g, b) for x, y, r, g, b in samples if _luma(r, g, b) <= dark_cut]

    if not ink_samples:
        raise ValueError(
            "Could not separate ink from paper in the reference image. "
            "Use a clear photo of dark writing on light paper."
        )

    ink_r = int(statistics.median([s[2] for s in ink_samples]))
    ink_g = int(statistics.median([s[3] for s in ink_samples]))
    ink_b = int(statistics.median([s[4] for s in ink_samples]))
    if paper_samples:
        paper_color = (
            int(statistics.median([p[0] for p in paper_samples])),
            int(statistics.median([p[1] for p in paper_samples])),
            int(statistics.median([p[2] for p in paper_samples])),
        )
    else:
        paper_color = (252, 252, 248)

    ink_lum = _luma(ink_r, ink_g, ink_b)
    paper_lum = _luma(*paper_color)
    contrast = max(0.0, min(1.0, (paper_lum - ink_lum) / 255.0))
    ink_opacity = max(0.55, min(0.98, 0.55 + contrast * 0.5))

    ink_points = [(s[0], s[1]) for s in ink_samples]
    slant = _estimate_slant(ink_points)

    # Build coarse mask at sample step for stroke width
    w, h = image.size
    step = 2
    mask_w, mask_h = (w + step - 1) // step, (h + step - 1) // step
    mask = [[False] * mask_w for _ in range(mask_h)]
    for x, y, r, g, b in ink_samples:
        mx, my = x // step, y // step
        if 0 <= my < mask_h and 0 <= mx < mask_w:
            mask[my][mx] = True
    mask_points = [(x // step, y // step) for x, y in ink_points]
    stroke_width = _estimate_stroke_width(mask, mask_points)

    ink_ratio = len(ink_samples) / float(len(samples))
    # Spacing heuristics from ink density
    if ink_ratio > 0.22:
        char_spacing, word_spacing = 0.98, 1.08
        relative_size = 1.05
    elif ink_ratio < 0.06:
        char_spacing, word_spacing = 1.1, 1.28
        relative_size = 0.96
    else:
        char_spacing, word_spacing = 1.04, 1.18
        relative_size = 1.0

    # Variation / drift from luminance spread of ink
    ink_lums = [_luma(s[2], s[3], s[4]) for s in ink_samples]
    spread = statistics.pstdev(ink_lums) if len(ink_lums) > 1 else 8.0
    variation = max(0.03, min(0.14, spread / 400.0))
    baseline_drift = max(0.3, min(1.8, 0.4 + variation * 12))
    line_drift = max(0.6, min(2.4, 0.8 + variation * 14))
    curvature = max(0.12, min(0.45, 0.15 + abs(slant) / 60.0 + variation))

    confidence = 0.35 + min(0.5, ink_ratio * 2.5) + min(0.15, contrast)
    if notes:
        confidence = max(0.2, confidence - 0.15)

    stat = ImageStat.Stat(image)
    _ = stat  # reserved for future texture metrics

    notes.append(
        "Matched visual identity (ink, slant, weight, spacing). "
        "Character outlines still use Level C glyph fallback until Level B cloning lands."
    )

    return ReferenceAnalysis(
        source_path=str(source.resolve()),
        ink_color=(ink_r, ink_g, ink_b),
        ink_opacity=ink_opacity,
        slant_degrees=slant,
        stroke_width=stroke_width,
        char_spacing=char_spacing,
        word_spacing=word_spacing,
        relative_size=relative_size,
        variation=variation,
        baseline_drift=baseline_drift,
        line_drift=line_drift,
        curvature=curvature,
        ink_ratio=ink_ratio,
        confidence=confidence,
        paper_color=paper_color,
        notes=notes,
    )


def profile_from_reference(
    path: str | Path,
    *,
    base_profile: str = "everyday",
    name: str = "reference_match",
) -> tuple[HandwritingProfile, ReferenceAnalysis]:
    """Build a document-wide handwriting profile from a reference photo."""
    analysis = analyze_reference_image(path)
    base = load_profile(base_profile)
    profile = HandwritingProfile(
        name=name,
        display_name=f"Reference match ({Path(path).name})",
        base_stroke_width=analysis.stroke_width,
        ink_color=analysis.ink_color,
        ink_opacity=analysis.ink_opacity,
        slant_degrees=analysis.slant_degrees,
        char_spacing=analysis.char_spacing,
        word_spacing=analysis.word_spacing,
        relative_size=analysis.relative_size,
        curvature=analysis.curvature,
        baseline_drift=analysis.baseline_drift,
        line_drift=analysis.line_drift,
        variation=analysis.variation,
        synthesis_level="C-reference",
        reference_image=str(Path(path).resolve()),
        reference_confidence=analysis.confidence,
    )
    # Keep mild base curvature blend when analysis is sparse
    if analysis.confidence < 0.45:
        profile = HandwritingProfile(
            name=profile.name,
            display_name=profile.display_name,
            base_stroke_width=(profile.base_stroke_width + base.base_stroke_width) / 2,
            ink_color=profile.ink_color,
            ink_opacity=profile.ink_opacity,
            slant_degrees=(profile.slant_degrees + base.slant_degrees) / 2,
            char_spacing=profile.char_spacing,
            word_spacing=profile.word_spacing,
            relative_size=profile.relative_size,
            curvature=(profile.curvature + base.curvature) / 2,
            baseline_drift=profile.baseline_drift,
            line_drift=profile.line_drift,
            variation=profile.variation,
            synthesis_level=profile.synthesis_level,
            reference_image=profile.reference_image,
            reference_confidence=profile.reference_confidence,
        )
        analysis.notes.append("Low confidence: blended with base preset for stability.")
    return profile, analysis


def reference_warnings(analysis: ReferenceAnalysis) -> list[WarningItem]:
    warnings = [
        WarningItem(
            code="reference_style_active",
            message=(
                f"Using reference handwriting style from '{Path(analysis.source_path).name}' "
                f"(confidence {analysis.confidence:.2f}). "
                "Visual identity matched; exact glyph cloning is not claimed in Phase 1."
            ),
            context=analysis.source_path,
        )
    ]
    for note in analysis.notes:
        if "Level C" in note or "Low" in note:
            warnings.append(
                WarningItem(
                    code="reference_match_note",
                    message=note,
                    severity="info" if "Level C" in note else "warning",
                )
            )
    return warnings
