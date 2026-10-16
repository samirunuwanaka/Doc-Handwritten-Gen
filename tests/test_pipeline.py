from pathlib import Path

from PIL import Image

from uniscript_ink.pipeline import render_file


def test_render_hello_jpg(tmp_path: Path):
    example = Path("examples/hello.txt")
    assert example.is_file()
    out = tmp_path / "out"
    result = render_file(
        example,
        out_dir=out,
        profile_name="everyday",
        paper_name="ruled",
        dpi=120,
        scan_mode="clean",
    )
    assert result.output_paths
    assert Path(result.manifest_path).is_file()
    img = Image.open(result.output_paths[0])
    assert img.size[0] > 100
    assert img.size[1] > 100
    assert result.profile.synthesis_level == "C"
    # Source unchanged
    assert "Hello from UniScript Ink" in example.read_text(encoding="utf-8")


def test_same_profile_across_pages(tmp_path: Path):
    # Long enough content to paginate at low DPI / large font path still ok
    text = "# Doc\n\n" + ("Consistent style line.\n\n" * 80)
    src = tmp_path / "long.md"
    src.write_text(text, encoding="utf-8")
    result = render_file(src, out_dir=tmp_path / "pages", profile_name="ballpoint", dpi=100)
    assert result.report["profile"]["name"] == "ballpoint"
    assert len(result.output_paths) >= 1
