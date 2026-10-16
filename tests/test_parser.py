from pathlib import Path

from uniscript_ink.ir import BlockKind
from uniscript_ink.parsers.text_md import parse_text_or_markdown


def test_markdown_headings_and_lists():
    text = "# Title\n\nHello\n\n- one\n- two\n"
    doc = parse_text_or_markdown(text, source_path="mem.md")
    kinds = [b.kind for b in doc.blocks]
    assert BlockKind.HEADING in kinds
    assert BlockKind.PARAGRAPH in kinds
    assert BlockKind.LIST_ITEM in kinds
    assert doc.title == "Title"


def test_unicode_preserved(tmp_path: Path):
    content = "café Ζεύς අකුරු"
    path = tmp_path / "u.txt"
    path.write_text(content, encoding="utf-8")
    from uniscript_ink.parsers.base import parse_document

    doc = parse_document(path)
    joined = " ".join(b.text for b in doc.blocks)
    assert "café" in joined
    assert "Ζεύς" in joined
    assert "අකුරු" in joined
    # Original untouched
    assert path.read_text(encoding="utf-8") == content
