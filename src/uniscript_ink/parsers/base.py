"""Parser registry — adapters return the shared Document IR."""

from __future__ import annotations

from pathlib import Path

from uniscript_ink.ir import Document, WarningItem
from uniscript_ink.parsers.text_md import parse_text_or_markdown

_SUPPORTED = {".txt", ".md", ".markdown"}


def parse_document(path: str | Path) -> Document:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Input not found: {source}")

    suffix = source.suffix.lower()
    # Read a copy of content only; never rewrite the original file.
    if suffix in _SUPPORTED:
        text = source.read_text(encoding="utf-8")
        doc = parse_text_or_markdown(text, source_path=str(source))
        return doc

    doc = Document(source_path=str(source))
    doc.warnings.append(
        WarningItem(
            code="unsupported_format",
            message=f"No Phase 1 adapter for '{suffix}'. Supported: .txt, .md",
            severity="error",
        )
    )
    raise ValueError(doc.warnings[0].message)
