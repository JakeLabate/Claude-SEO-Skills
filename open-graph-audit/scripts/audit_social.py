#!/usr/bin/env python3
"""Audit an Open Graph / Twitter Card inventory and emit findings.

Usage:
    python3 audit_social.py social_inventory.json [--output audit_report.json]

Checks (see references/audit-checks.md):
- missing_og_title / missing_og_description / missing_og_image (high/medium)
- missing_og_url (medium); og_url_mismatch (medium) vs. canonical/final URL
- og_image_broken (high): og:image returns non-200
- og_image_not_image (medium): og:image content-type is not image/*
- og_image_relative (medium): og:image is not an absolute URL
- missing_twitter_card (low): no twitter:card and no OG to fall back on
- og_description_too_long (low > 300 chars) / og_title_too_long (low > 90)
- duplicate_og_image (info): same share image across many pages

Uses only the Python standard library.
"""

import argparse
import json
import sys
import urllib.parse
from collections import defaultdict

OG_TITLE_MAX = 90
OG_DESC_MAX = 300


def norm(url):
    if not url:
        return ""
    u = urllib.parse.urldefrag(url)[0].rstrip("/")
    return u


def main():
    ap = argparse.ArgumentParser(description="Run Open Graph / Twitter Card audit checks.")
    ap.add_argument("inventory")
    ap.add_argument("--output", default="audit_report.json")
    args = ap.parse_args()

    with open(args.inventory, encoding="utf-8") as f:
        data = json.load(f)
    pages = data.get("pages", {})
    images = data.get("images", {})

    findings = {k: [] for k in (
        "missing_og_title", "missing_og_description", "missing_og_image",
        "missing_og_url", "og_url_mismatch", "og_image_broken",
        "og_image_not_image", "og_image_relative", "missing_twitter_card",
        "og_title_too_long", "og_description_too_long", "duplicate_og_image")}

    image_use = defaultdict(list)

    for url, page in pages.items():
        if page.get("status", 0) != 200:
            continue
        if "noindex" in (page.get("meta_robots") or "").lower():
            continue
        og = page.get("og", {})
        tw = page.get("twitter", {})
        final_url = page.get("final_url", url)
        canonical = page.get("canonical")

        if not og.get("og:title"):
            findings["missing_og_title"].append({"page": url})
        elif len(og["og:title"]) > OG_TITLE_MAX:
            findings["og_title_too_long"].append(
                {"page": url, "length": len(og["og:title"]), "value": og["og:title"]})

        if not og.get("og:description"):
            findings["missing_og_description"].append({"page": url})
        elif len(og["og:description"]) > OG_DESC_MAX:
            findings["og_description_too_long"].append(
                {"page": url, "length": len(og["og:description"])})

        image = og.get("og:image") or og.get("og:image:secure_url")
        if not image:
            findings["missing_og_image"].append({"page": url})
        else:
            image_use[image].append(url)
            info = images.get(image, {})
            if info:
                if not info.get("absolute", True):
                    findings["og_image_relative"].append({"page": url, "og_image": image})
                elif info.get("status", 0) == 0 or info.get("status", 0) >= 400:
                    findings["og_image_broken"].append(
                        {"page": url, "og_image": image, "status": info.get("status")})
                elif "image" not in (info.get("content_type") or ""):
                    findings["og_image_not_image"].append(
                        {"page": url, "og_image": image, "content_type": info.get("content_type")})

        og_url = og.get("og:url")
        if not og_url:
            findings["missing_og_url"].append({"page": url})
        else:
            expected = norm(canonical) or norm(final_url)
            if norm(og_url) != expected:
                findings["og_url_mismatch"].append(
                    {"page": url, "og_url": og_url, "expected": expected})

        if not tw.get("twitter:card") and not og:
            findings["missing_twitter_card"].append({"page": url})

    for image, urls in image_use.items():
        if len(urls) > 5:
            findings["duplicate_og_image"].append(
                {"og_image": image, "page_count": len(urls), "examples": sorted(urls)[:5]})

    severity = {
        "missing_og_title": "high", "missing_og_image": "high", "og_image_broken": "high",
        "missing_og_description": "medium", "missing_og_url": "medium",
        "og_url_mismatch": "medium", "og_image_not_image": "medium",
        "og_image_relative": "medium",
        "missing_twitter_card": "low", "og_title_too_long": "low",
        "og_description_too_long": "low", "duplicate_og_image": "info",
    }
    summary = {
        "pages_analyzed": sum(1 for p in pages.values() if p.get("status", 0) == 200),
        "share_images_probed": len(images),
        "issues_by_check": {k: len(v) for k, v in findings.items()},
        "issues_by_severity": {
            level: sum(len(findings[k]) for k, s in severity.items() if s == level)
            for level in ("high", "medium", "low", "info")},
    }
    report = {"summary": summary, "severity": severity, "findings": findings}
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(json.dumps(summary, indent=2))
    print(f"Full report written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
