"""Page layout and paper presets."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from PIL import ImageFont

from uniscript_ink.handwriting.profiles import HandwritingProfile
from uniscript_ink.ir import Block, BlockKind, Document, WarningItem

_ROOT = Path(__file__).resolve().parents[3]
_PAPER_PATH = _ROOT / "configs" / "paper.yaml"

# A4 at given DPI
_A4_INCH = (8.27, 11.69)


@dataclass
class LineBox:
    text: str
    x: float
    y: float
    font_size: int
    kind: BlockKind
    baseline_jitter: float = 0.0


@dataclass
class PageSpec:
    index: int
    width: int
    height: int
    lines: list[LineBox] = field(default_factory=list)
    paper: dict[str, Any] = field(default_factory=dict)


def load_paper(name: str) -> dict[str, Any]:
    data = yaml.safe_load(_PAPER_PATH.read_text(encoding="utf-8"))
    if name not in data:
        raise KeyError(f"Unknown paper '{name}'. Known: {', '.join(sorted(data))}")
    paper = dict(data[name])
    paper["name"] = name
    return paper


def list_papers() -> list[str]:
    data = yaml.safe_load(_PAPER_PATH.read_text(encoding="utf-8"))
    return sorted(data)


def _font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(font_path, size=size)


def _wrap_text(
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: float,
    profile: HandwritingProfile,
) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        width = font.getlength(trial) * profile.char_spacing
        if width <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def layout_document(
    doc: Document,
    profile: HandwritingProfile,
    paper: dict[str, Any],
    font_path: str,
    dpi: int = 200,
) -> list[PageSpec]:
    width = int(_A4_INCH[0] * dpi)
    height = int(_A4_INCH[1] * dpi)
    margin = float(paper.get("margin_pt", 54)) * dpi / 72.0
    content_width = width - 2 * margin
    y = margin
    line_gap = float(paper.get("line_spacing_pt") or 28) * dpi / 72.0
    pages: list[PageSpec] = []
    current = PageSpec(index=0, width=width, height=height, paper=paper)

    def new_page() -> None:
        nonlocal current, y
        pages.append(current)
        current = PageSpec(index=len(pages), width=width, height=height, paper=paper)
        y = margin

    def ensure_space(needed: float) -> None:
        nonlocal y
        if y + needed > height - margin:
            new_page()

    base_size = max(14, int(18 * profile.relative_size * dpi / 150))

    for block in doc.blocks:
        if block.kind == BlockKind.PAGEBREAK:
            new_page()
            continue
        if block.kind == BlockKind.HORIZONTAL_RULE:
            ensure_space(line_gap)
            current.lines.append(
                LineBox(text="—", x=margin, y=y, font_size=base_size, kind=block.kind)
            )
            y += line_gap
            continue

        size = base_size
        if block.kind == BlockKind.HEADING:
            size = int(base_size * (1.6 - 0.1 * max(block.level - 1, 0)))
        prefix = ""
        if block.kind == BlockKind.LIST_ITEM:
            if block.meta.get("ordered"):
                prefix = f"{block.meta.get('index', 1)}. "
            else:
                prefix = "• "
        text = prefix + block.text
        font = _font(font_path, size)
        wrapped = _wrap_text(text, font, content_width, profile)
        for i, line in enumerate(wrapped):
            ensure_space(line_gap * 1.1)
            indent = margin
            if block.kind == BlockKind.LIST_ITEM:
                indent += float(block.meta.get("indent", 0)) * 4
            jitter = profile.baseline_drift * (0.5 if i == 0 else 1.0)
            current.lines.append(
                LineBox(
                    text=line,
                    x=indent,
                    y=y,
                    font_size=size,
                    kind=block.kind,
                    baseline_jitter=jitter,
                )
            )
            y += line_gap * (1.15 if block.kind == BlockKind.HEADING else 1.0)
            y += profile.line_drift * 0.15
        y += line_gap * 0.25

    if current.lines or not pages:
        pages.append(current)

    # Soft overflow check
    for page in pages:
        for line in page.lines:
            if line.y > page.height - margin * 0.5:
                doc.warnings.append(
                    WarningItem(
                        code="possible_clipping",
                        message=f"Line may approach bottom margin on page {page.index + 1}.",
                        context=line.text[:60],
                    )
                )
    return pages
