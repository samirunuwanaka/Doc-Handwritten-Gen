"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys

from uniscript_ink import __version__
from uniscript_ink.handwriting.profiles import list_profiles
from uniscript_ink.handwriting.reference import profile_from_reference
from uniscript_ink.layout.paginate import list_papers
from uniscript_ink.pipeline import render_file


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="uniscript-ink",
        description="UniScript Ink — multilingual handwriting document renderer",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    render = sub.add_parser("render", help="Render a document to handwritten page images")
    render.add_argument("input", help="Path to .txt or .md file")
    render.add_argument("--out", default="results/generated", help="Output directory")
    render.add_argument(
        "--profile",
        default="everyday",
        help="Handwriting profile preset (also used as base when --reference is set)",
    )
    render.add_argument(
        "--reference",
        default=None,
        help="Optional photo of your handwriting; style identity is matched for the whole job",
    )
    render.add_argument("--paper", default="ruled", help="Paper style name")
    render.add_argument("--dpi", type=int, default=200, help="Output DPI (A4)")
    render.add_argument(
        "--scan",
        choices=("clean", "subtle"),
        default="clean",
        help="Scan simulation mode (default: clean)",
    )
    render.add_argument("--format", choices=("jpg", "png"), default="jpg")
    render.add_argument("--quality", type=int, default=92, help="JPEG quality")

    analyze = sub.add_parser(
        "analyze-reference",
        help="Inspect a handwriting photo and print the derived style metrics",
    )
    analyze.add_argument("image", help="Path to handwriting reference image")
    analyze.add_argument(
        "--base-profile",
        default="everyday",
        help="Preset to blend with when confidence is low",
    )

    sub.add_parser("profiles", help="List handwriting profiles")
    sub.add_parser("papers", help="List paper styles")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "profiles":
        for name in list_profiles():
            print(name)
        return 0
    if args.command == "papers":
        for name in list_papers():
            print(name)
        return 0
    if args.command == "analyze-reference":
        try:
            profile, analysis = profile_from_reference(
                args.image,
                base_profile=args.base_profile,
            )
        except (FileNotFoundError, ValueError, KeyError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(analysis.to_dict(), indent=2, ensure_ascii=False))
        print(json.dumps(profile.to_manifest(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "render":
        try:
            result = render_file(
                args.input,
                out_dir=args.out,
                profile_name=args.profile,
                paper_name=args.paper,
                dpi=args.dpi,
                scan_mode=args.scan,
                image_format=args.format,
                quality=args.quality,
                reference_image=args.reference,
            )
        except (FileNotFoundError, ValueError, KeyError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"Wrote {len(result.output_paths)} page(s)")
        for path in result.output_paths:
            print(f"  {path}")
        print(f"Manifest: {result.manifest_path}")
        warnings = result.report.get("warnings") or []
        if warnings:
            print(f"Warnings ({len(warnings)}):")
            for w in warnings:
                print(f"  [{w['code']}] {w['message']}")
        payload = {
            "scripts": result.report.get("scripts_present"),
            "level": result.profile.synthesis_level,
            "reference": bool(result.profile.reference_image),
        }
        print(json.dumps(payload))
        return 0
    parser.error(f"unknown command {args.command}")
    return 2
