"""Quality and content-integrity report."""

from __future__ import annotations

from typing import Any

from uniscript_ink.ir import Document


def build_quality_report(doc: Document, page_count: int, output_paths: list[str]) -> dict[str, Any]:
    return {
        "source_path": doc.source_path,
        "title": doc.title,
        "page_count": page_count,
        "scripts_present": doc.meta.get("scripts_present", []),
        "script_counts": doc.meta.get("script_counts", {}),
        "synthesis_level": doc.meta.get("synthesis_level", "C"),
        "font": doc.meta.get("font_path"),
        "warnings": [
            {
                "code": w.code,
                "message": w.message,
                "severity": w.severity,
                "context": w.context,
            }
            for w in doc.warnings
        ],
        "outputs": output_paths,
        "integrity_policy": (
            "Missing glyphs and unsupported features are reported; "
            "scan effects are not used to hide rendering errors."
        ),
    }
