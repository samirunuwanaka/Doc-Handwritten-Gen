"""Script detection and coverage reporting."""

from __future__ import annotations

import unicodedata
from collections import Counter

from uniscript_ink.ir import Document, ScriptRun, WarningItem

# Unicode ranges approximate common writing systems for Phase 1 detection.
_SCRIPT_RANGES: list[tuple[str, int, int, str]] = [
    ("latin", 0x0041, 0x024F, "ltr"),
    ("latin", 0x1E00, 0x1EFF, "ltr"),
    ("greek", 0x0370, 0x03FF, "ltr"),
    ("cyrillic", 0x0400, 0x04FF, "ltr"),
    ("hebrew", 0x0590, 0x05FF, "rtl"),
    ("arabic", 0x0600, 0x06FF, "rtl"),
    ("arabic", 0x0750, 0x077F, "rtl"),
    ("devanagari", 0x0900, 0x097F, "ltr"),
    ("bengali", 0x0980, 0x09FF, "ltr"),
    ("tamil", 0x0B80, 0x0BFF, "ltr"),
    ("sinhala", 0x0D80, 0x0DFF, "ltr"),
    ("thai", 0x0E00, 0x0E7F, "ltr"),
    ("cjk", 0x3040, 0x30FF, "ltr"),  # kana
    ("cjk", 0x3400, 0x4DBF, "ltr"),
    ("cjk", 0x4E00, 0x9FFF, "ltr"),
    ("cjk", 0xAC00, 0xD7AF, "ltr"),  # hangul
    ("cjk", 0xF900, 0xFAFF, "ltr"),
]

_RTL_SCRIPTS = {"arabic", "hebrew"}
_NEEDS_SHAPING = {"arabic", "hebrew", "devanagari", "bengali", "tamil", "sinhala", "thai"}


def detect_script(char: str) -> tuple[str, str]:
    if not char or char.isspace() or unicodedata.category(char).startswith("P"):
        return ("common", "ltr")
    if char.isascii() and (char.isalnum() or char in "'-\""):
        return ("latin", "ltr")
    code = ord(char)
    for name, start, end, direction in _SCRIPT_RANGES:
        if start <= code <= end:
            return (name, direction)
    return ("unknown", "ltr")


def split_script_runs(text: str) -> list[ScriptRun]:
    text = unicodedata.normalize("NFC", text)
    if not text:
        return []
    runs: list[ScriptRun] = []
    current_script: str | None = None
    current_dir = "ltr"
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf, current_script, current_dir
        if buf and current_script is not None:
            runs.append(ScriptRun("".join(buf), current_script, current_dir))
        buf = []

    for ch in text:
        script, direction = detect_script(ch)
        if script == "common":
            if current_script is None:
                current_script = "latin"
                current_dir = "ltr"
            buf.append(ch)
            continue
        if current_script is None:
            current_script = script
            current_dir = direction
            buf.append(ch)
            continue
        if script == current_script:
            buf.append(ch)
        else:
            flush()
            current_script = script
            current_dir = direction
            buf.append(ch)
    flush()
    return runs


def annotate_document(doc: Document) -> Document:
    counts: Counter[str] = Counter()
    for block in doc.blocks:
        if not block.text:
            continue
        block.runs = split_script_runs(block.text)
        for run in block.runs:
            counts[run.script] += len(run.text)

    rtl = sorted(s for s in counts if s in _RTL_SCRIPTS)
    if rtl:
        doc.warnings.append(
            WarningItem(
                code="rtl_shaping_pending",
                message=(
                    "RTL scripts detected ("
                    + ", ".join(rtl)
                    + "). Full HarfBuzz/FriBidi shaping is planned; Phase 1 uses best-effort glyph placement."
                ),
                context=",".join(rtl),
            )
        )

    shaping = sorted(s for s in counts if s in _NEEDS_SHAPING)
    if shaping:
        doc.warnings.append(
            WarningItem(
                code="complex_shaping_experimental",
                message=(
                    "Complex scripts present ("
                    + ", ".join(shaping)
                    + "). Rendering is experimental until dedicated shaping tests pass."
                ),
                context=",".join(shaping),
            )
        )

    if "unknown" in counts:
        doc.warnings.append(
            WarningItem(
                code="unknown_script_chars",
                message="Some characters could not be classified into a known script.",
                severity="warning",
            )
        )

    doc.meta["script_counts"] = dict(counts)
    doc.meta["scripts_present"] = sorted(counts)
    return doc
