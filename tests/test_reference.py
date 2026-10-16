from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from uniscript_ink.handwriting.fonts import resolve_font_path
from uniscript_ink.handwriting.reference import analyze_reference_image, profile_from_reference
from uniscript_ink.pipeline import render_file


def _make_reference(path: Path, ink: tuple[int, int, int] = (20, 45, 120), slanted: bool = True) -> Path:
    img = Image.new("RGB", (640, 240), (250, 248, 240))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(resolve_font_path(), 42)
    text = "My handwriting sample"
    # Draw slightly thick ink strokes
    for dx, dy in ((0, 0), (1, 0), (0, 1)):
        x = 40 + dx + (8 if slanted else 0)
        y = 90 + dy
        draw.text((x, y), text, font=font, fill=ink)
    img.save(path, format="PNG")
    return path


def test_analyze_reference_extracts_ink(tmp_path: Path):
    ref = _make_reference(tmp_path / "hand.png", ink=(18, 40, 130))
    analysis = analyze_reference_image(ref)
    assert analysis.confidence > 0.2
    # Ink should be bluish / dark, not paper-white
    assert analysis.ink_color[2] > analysis.ink_color[0] or sum(analysis.ink_color) < 200
    data = analysis.to_dict()
    assert data["exact_glyph_cloning"] is False
    assert data["match_mode"] == "visual_identity_level_C"


def test_profile_from_reference(tmp_path: Path):
    ref = _make_reference(tmp_path / "hand2.png")
    profile, analysis = profile_from_reference(ref, base_profile="everyday")
    assert profile.reference_image is not None
    assert profile.synthesis_level.startswith("C")
    assert profile.ink_color == analysis.ink_color


def test_render_with_reference(tmp_path: Path):
    ref = _make_reference(tmp_path / "ref.png", ink=(30, 30, 30))
    src = tmp_path / "note.txt"
    src.write_text("Reference style should apply to every line.\n", encoding="utf-8")
    result = render_file(
        src,
        out_dir=tmp_path / "out",
        profile_name="everyday",
        paper_name="blank",
        dpi=100,
        reference_image=ref,
    )
    assert result.profile.reference_image is not None
    assert result.report.get("reference_analysis")
    assert Path(result.output_paths[0]).is_file()
    assert any(w["code"] == "reference_style_active" for w in result.report["warnings"])
