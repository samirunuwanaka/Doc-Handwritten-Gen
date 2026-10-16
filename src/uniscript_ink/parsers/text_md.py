"""Plain text and lightweight Markdown adapter."""

from __future__ import annotations

import re

from uniscript_ink.ir import Block, BlockKind, Document, WarningItem

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_UL = re.compile(r"^(\s*)([-*+])\s+(.*)$")
_OL = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
_HR = re.compile(r"^(\*{3,}|-{3,}|_{3,})\s*$")
_FENCE = re.compile(r"^```")


def parse_text_or_markdown(text: str, source_path: str) -> Document:
    doc = Document(source_path=source_path)
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    paragraph: list[str] = []
    in_fence = False
    fence_buf: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            body = " ".join(part.strip() for part in paragraph if part.strip())
            if body:
                doc.blocks.append(Block(kind=BlockKind.PARAGRAPH, text=body))
            paragraph = []

    for raw in lines:
        if _FENCE.match(raw.strip()):
            if in_fence:
                flush_paragraph()
                code = "\n".join(fence_buf)
                doc.blocks.append(
                    Block(
                        kind=BlockKind.PARAGRAPH,
                        text=code,
                        meta={"code_block": True},
                    )
                )
                fence_buf = []
                in_fence = False
            else:
                flush_paragraph()
                in_fence = True
            continue

        if in_fence:
            fence_buf.append(raw)
            continue

        if not raw.strip():
            flush_paragraph()
            continue

        if _HR.match(raw.strip()):
            flush_paragraph()
            doc.blocks.append(Block(kind=BlockKind.HORIZONTAL_RULE))
            continue

        heading = _HEADING.match(raw)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            title = heading.group(2).strip()
            doc.blocks.append(Block(kind=BlockKind.HEADING, text=title, level=level))
            if doc.title is None and level == 1:
                doc.title = title
            continue

        ul = _UL.match(raw)
        if ul:
            flush_paragraph()
            doc.blocks.append(
                Block(
                    kind=BlockKind.LIST_ITEM,
                    text=ul.group(3).strip(),
                    meta={"ordered": False, "indent": len(ul.group(1))},
                )
            )
            continue

        ol = _OL.match(raw)
        if ol:
            flush_paragraph()
            doc.blocks.append(
                Block(
                    kind=BlockKind.LIST_ITEM,
                    text=ol.group(3).strip(),
                    meta={
                        "ordered": True,
                        "index": int(ol.group(2)),
                        "indent": len(ol.group(1)),
                    },
                )
            )
            continue

        if "|" in raw and raw.strip().startswith("|"):
            flush_paragraph()
            doc.blocks.append(Block(kind=BlockKind.PARAGRAPH, text=raw.strip()))
            doc.warnings.append(
                WarningItem(
                    code="table_as_text",
                    message="Markdown table row rendered as plain text in Phase 1.",
                    context=raw.strip()[:80],
                )
            )
            continue

        paragraph.append(raw)

    if in_fence and fence_buf:
        doc.blocks.append(
            Block(kind=BlockKind.PARAGRAPH, text="\n".join(fence_buf), meta={"code_block": True})
        )
    flush_paragraph()

    if not doc.blocks:
        doc.warnings.append(
            WarningItem(
                code="empty_document",
                message="Document contained no extractable text blocks.",
                severity="warning",
            )
        )
    return doc
