#!/usr/bin/env python3
"""Audit an image inventory JSON (from extract_images.py) and emit audit findings.

Usage:
    python3 audit_images.py image_inventory.json [--output audit_report.json]
        [--max-bytes 200000] [--lazy-after 1]

Checks implemented (see references/audit-checks.md):
- missing_alt: <img> with no alt attribute at all (high)
- broken_image: image URL returns a non-200 status (high, needs --check-files)
- empty_alt: alt="" — valid only for decorative images, flagged for review (info)
- missing_dimensions: no width and/or height attribute, risking layout shift (medium)
- oversized_file: image larger than --max-bytes (medium, needs --check-files)
- not_lazy_loaded: img beyond --lazy-after on the page without loading="lazy" (low)
- legacy_format: jpg/png/gif served without a modern <picture> source (low)
- generic_filename: uninformative filename (e.g. IMG_1234, screenshot, untitled) (low)
- alt_too_long: alt text over 125 characters (low)
- redundant_alt: alt text starting with "image of"/"photo of"/"picture of" (low)
- duplicate_alt: identical non-empty alt reused across many distinct images (info)

Uses only the Python standard library.
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
from collections import Counter, defaultdict

ALT_MAX = 125
MODERN_FORMATS = {"webp", "avif", "svg"}
LEGACY_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "bmp", "tiff"}
GENERIC_PATTERNS = [
    re.compile(r"^img[\W_]*\d+$", re.I),
    re.compile(r"^image[\W_]*\d*$", re.I),
    re.compile(r"^dsc[\W_]*\d+$", re.I),
    re.compile(r"^dscn[\W_]*\d+$", re.I),
    re.compile(r"^photo[\W_]*\d*$", re.I),
    re.compile(r"^pic[\W_]*\d*$", re.I),
    re.compile(r"^screen ?shot.*$", re.I),
    re.compile(r"^screenshot.*$", re.I),
    re.compile(r"^untitled.*$", re.I),
    re.compile(r"^download.*$", re.I),
    re.compile(r"^[0-9a-f]{16,}$", re.I),      # hash-like names
    re.compile(r"^\d{6,}$"),                     # all-digit names
]
REDUNDANT_PREFIXES = ("image of", "picture of", "photo of", "graphic of", "a picture of")


def filename_stem(src):
    path = urllib.parse.urlparse(src).path
    base = os.path.basename(path)
    stem, _ext = os.path.splitext(base)
    return urllib.parse.unquote(stem)


def extension(src):
    path = urllib.parse.urlparse(src).path
    return os.path.splitext(path)[1].lower().lstrip(".")


def main():
    ap = argparse.ArgumentParser(description="Run image SEO audit checks.")
    ap.add_argument("inventory", help="image_inventory.json from extract_images.py")
    ap.add_argument("--output", default="audit_report.json")
    ap.add_argument("--max-bytes", type=int, default=200_000,
                    help="flag images larger than this many bytes (default 200000)")
    ap.add_argument("--lazy-after", type=int, default=1,
                    help="images at this 0-based position or later should be lazy-loaded")
    args = ap.parse_args()

    with open(args.inventory, encoding="utf-8") as f:
        data = json.load(f)
    pages = data.get("pages", {})
    files = data.get("files", {})
    checked = data.get("checked_files", False)

    findings = {
        "missing_alt": [], "broken_image": [], "empty_alt": [],
        "missing_dimensions": [], "oversized_file": [], "not_lazy_loaded": [],
        "legacy_format": [], "generic_filename": [], "alt_too_long": [],
        "redundant_alt": [], "duplicate_alt": [],
    }

    total_images = 0
    with_alt = 0
    alt_to_srcs = defaultdict(set)

    for url, page in pages.items():
        if page.get("status", 200) != 200:
            continue
        for img in page.get("images", []):
            total_images += 1
            src = img.get("src")
            alt = img.get("alt")
            where = {"page": url, "src": src}

            # Alt text
            if alt is None:
                findings["missing_alt"].append(where)
            elif alt.strip() == "":
                findings["empty_alt"].append(where)
            else:
                with_alt += 1
                alt_to_srcs[" ".join(alt.lower().split())].add(src)
                if len(alt) > ALT_MAX:
                    findings["alt_too_long"].append({**where, "alt": alt, "length": len(alt)})
                if alt.lower().lstrip().startswith(REDUNDANT_PREFIXES):
                    findings["redundant_alt"].append({**where, "alt": alt})

            # Dimensions
            if not img.get("width") or not img.get("height"):
                findings["missing_dimensions"].append(where)

            # Lazy loading
            if (img.get("position", 0) >= args.lazy_after
                    and img.get("loading") != "lazy"):
                findings["not_lazy_loaded"].append({**where, "position": img.get("position")})

            # Format / filename (need a real src)
            if src:
                ext = extension(src)
                if ext in LEGACY_EXTENSIONS and not img.get("in_picture"):
                    findings["legacy_format"].append({**where, "format": ext})
                stem = filename_stem(src)
                if stem and any(p.match(stem) for p in GENERIC_PATTERNS):
                    findings["generic_filename"].append({**where, "filename": stem})

            # File-level checks (only when extract was run with --check-files)
            if checked and src in files:
                info = files[src]
                if info.get("status", 0) >= 400 or info.get("status", 0) == 0:
                    findings["broken_image"].append({**where, "status": info.get("status")})
                size = info.get("bytes")
                if size and size > args.max_bytes:
                    findings["oversized_file"].append({**where, "bytes": size})

    # Duplicate alt: same alt text across 3+ distinct image URLs
    for alt, srcs in alt_to_srcs.items():
        if len(srcs) >= 3:
            findings["duplicate_alt"].append({"alt": alt, "count": len(srcs),
                                              "examples": sorted(srcs)[:5]})

    severity = {
        "missing_alt": "high", "broken_image": "high",
        "missing_dimensions": "medium", "oversized_file": "medium",
        "not_lazy_loaded": "low", "legacy_format": "low",
        "generic_filename": "low", "alt_too_long": "low", "redundant_alt": "low",
        "empty_alt": "info", "duplicate_alt": "info",
    }
    summary = {
        "pages_analyzed": sum(1 for p in pages.values() if p.get("status", 200) == 200),
        "images_found": total_images,
        "images_with_alt": with_alt,
        "alt_coverage_pct": round(100 * with_alt / total_images, 1) if total_images else 0,
        "checked_files": checked,
        "issues_by_check": {k: len(v) for k, v in findings.items()},
        "issues_by_severity": {
            level: sum(len(findings[k]) for k, s in severity.items() if s == level)
            for level in ("high", "medium", "low", "info")
        },
    }
    report = {"summary": summary, "severity": severity, "findings": findings}

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(json.dumps(summary, indent=2))
    print(f"Full report written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
