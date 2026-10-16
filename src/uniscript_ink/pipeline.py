"""End-to-end render pipeline for UniScript Ink Phase 1."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from uniscript_ink.export.jpg import export_images, write_manifest
from uniscript_ink.handwriting.fonts import font_warning_if_needed, resolve_font_path
from uniscript_ink.handwriting.profiles import HandwritingProfile, load_profile
from uniscript_ink.languages.scripts import annotate_document
from uniscript_ink.layout.paginate import layout_document, load_paper
from uniscript_ink.parsers.base import parse_document
from uniscript_ink.quality.report import build_quality_report
from uniscript_ink.rendering.raster import render_pages
from uniscript_ink.scanning.simulate import apply_scan


@dataclass
class RenderResult:
    output_paths: list[str]
    manifest_path: str
    report: dict[str, Any]
    profile: HandwritingProfile


def render_file(
    input_path: str | Path,
    out_dir: str | Path,
    profile_name: str = "everyday",
    paper_name: str = "ruled",
    dpi: int = 200,
    scan_mode: str = "clean",
    image_format: str = "jpg",
    quality: int = 92,
) -> RenderResult:
    source = Path(input_path)
    # Parse from a content copy; original file is never written.
    doc = parse_document(source)
    doc = annotate_document(doc)

    profile = load_profile(profile_name)
    paper = load_paper(paper_name)
    font_path = resolve_font_path()
    warn = font_warning_if_needed(font_path)
    if warn:
        doc.warnings.append(warn)

    pages = layout_document(doc, profile, paper, font_path, dpi=dpi)
    images = render_pages(doc, pages, profile, font_path)
    images = [apply_scan(img, mode=scan_mode) for img in images]

    stem = source.stem
    paths = export_images(images, out_dir, stem=stem, fmt=image_format, quality=quality)
    report = build_quality_report(doc, page_count=len(images), output_paths=paths)
    report["profile"] = profile.to_manifest()
    report["paper"] = paper.get("name", paper_name)
    report["dpi"] = dpi
    report["scan_mode"] = scan_mode
    report["image_format"] = image_format

    manifest_path = write_manifest(Path(out_dir) / f"{stem}_manifest.json", report)
    return RenderResult(
        output_paths=paths,
        manifest_path=manifest_path,
        report=report,
        profile=profile,
    )
