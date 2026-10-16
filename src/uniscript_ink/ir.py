"""Structured document intermediate representation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BlockKind(str, Enum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    LIST_ITEM = "list_item"
    EQUATION = "equation"
    TABLE = "table"
    FIGURE = "figure"
    PAGEBREAK = "pagebreak"
    HORIZONTAL_RULE = "horizontal_rule"


@dataclass
class WarningItem:
    code: str
    message: str
    severity: str = "warning"
    context: str | None = None


@dataclass
class ScriptRun:
    text: str
    script: str
    direction: str = "ltr"


@dataclass
class Block:
    kind: BlockKind
    text: str = ""
    level: int = 0
    runs: list[ScriptRun] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Document:
    source_path: str
    title: str | None = None
    blocks: list[Block] = field(default_factory=list)
    warnings: list[WarningItem] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
