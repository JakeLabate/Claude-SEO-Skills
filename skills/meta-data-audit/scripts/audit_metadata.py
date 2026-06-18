#!/usr/bin/env python3
"""Audit a metadata inventory JSON (from extract_metadata.py) and emit audit findings.

Usage:
    python3 audit_metadata.py metadata_inventory.json [--output audit_report.json]
        [--brand-suffix "| Acme Co"] [--include-noindex]

Checks implemented (see references/audit-checks.md):
- missing_title: no or empty <title> (high)
- missing_description: no or empty meta description (high)
- duplicate_titles: identical title on 2+ indexable pages (high)
- duplicate_descriptions: identical description on 2+ indexable pages (high)
- multiple_titles / multiple_descriptions: more than one tag on a page (medium)
- title_too_long (> 60 chars) / title_too_short (< 30 chars) (medium)
- description_too_long (> 160 chars) / description_too_short (< 70 chars) (medium)
- generic_title: boilerplate or brand-only titles (medium)
- description_duplicates_title: description equals or contains only the title (low)
- keyword_stuffing: same significant word 3+ times in a title (low)
- title_h1_mismatch: title and H1 share no significant words (informational)

Uses only the Python standard library.
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict

TITLE_MAX = 60
TITLE_MIN = 30
DESC_MAX = 160
DESC_MIN = 70

GENERIC_TITLES = {
    "home", "homepage", "index", "untitled", "untitled page", "new page",
    "default", "page", "welcome", "blog", "about", "about us", "contact",
    "contact us", "products", "services",
}
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in",
    "is", "it", "of", "on", "or", "the", "to", "with", "your", "you", "our",
}


def words(text):
    return [w for w in re.findall(r"[a-z0-9']+", text.lower()) if w not in STOPWORDS]


def strip_brand(text, brand_suffix):
    if not brand_suffix:
        return text.strip()
    stripped = text.strip()
    brand = brand_suffix.strip()
    if stripped.lower().endswith(brand.lower()):
        stripped = stripped[: len(stripped) - len(brand)].rstrip(" |-–:·")
    return stripped


def is_noindex(page):
    return "noindex" in (page.get("meta_robots") or "").lower()


def main():
    ap = argparse.ArgumentParser(description="Run title/meta description audit checks.")
    ap.add_argument("inventory", help="metadata_inventory.json from extract_metadata.py")
    ap.add_argument("--output", default="audit_report.json")
    ap.add_argument("--brand-suffix", default="",
                    help='brand pattern appended to titles, e.g. "| Acme Co"')
    ap.add_argument("--include-noindex", action="store_true",
                    help="include noindexed pages in duplicate checks")
    args = ap.parse_args()

    with open(args.inventory, encoding="utf-8") as f:
        data = json.load(f)
    pages = data.get("pages", {})

    findings = {
        "missing_title": [], "missing_description": [],
        "duplicate_titles": [], "duplicate_descriptions": [],
        "multiple_titles": [], "multiple_descriptions": [],
        "title_too_long": [], "title_too_short": [],
        "description_too_long": [], "description_too_short": [],
        "generic_title": [],
        "description_duplicates_title": [], "keyword_stuffing": [],
        "title_h1_mismatch": [],
    }

    title_groups = defaultdict(list)
    desc_groups = defaultdict(list)
    bands = {"title": Counter(), "description": Counter()}

    for url, page in pages.items():
        if page.get("status", 200) != 200:
            continue
        titles = [t for t in page.get("titles", [])]
        descs = [d for d in page.get("descriptions", [])]
        title = next((t for t in titles if t.strip()), "")
        desc = next((d for d in descs if d.strip()), "")
        noindex = is_noindex(page)

        # Missing / multiple
        if not title:
            findings["missing_title"].append({"page": url, "h1": page.get("h1")})
            bands["title"]["missing"] += 1
        if not desc:
            findings["missing_description"].append({"page": url, "h1": page.get("h1")})
            bands["description"]["missing"] += 1
        if len([t for t in titles if t.strip()]) > 1:
            findings["multiple_titles"].append({"page": url, "count": len(titles), "values": titles})
        if len([d for d in descs if d.strip()]) > 1:
            findings["multiple_descriptions"].append({"page": url, "count": len(descs), "values": descs})

        # Title checks
        if title:
            n = len(title)
            entry = {"page": url, "title": title, "length": n}
            if n > TITLE_MAX:
                findings["title_too_long"].append(entry)
                bands["title"]["too_long"] += 1
            elif n < TITLE_MIN:
                findings["title_too_short"].append(entry)
                bands["title"]["too_short"] += 1
            else:
                bands["title"]["good"] += 1

            core = strip_brand(title, args.brand_suffix)
            if core.lower() in GENERIC_TITLES or not core:
                findings["generic_title"].append({"page": url, "title": title})

            counts = Counter(words(core))
            stuffed = [w for w, c in counts.items() if c >= 3 and len(w) > 2]
            if stuffed:
                findings["keyword_stuffing"].append(
                    {"page": url, "title": title, "repeated": stuffed})

            if not noindex or args.include_noindex:
                key = " ".join(core.lower().split())
                if key:
                    title_groups[key].append(url)

            h1 = page.get("h1")
            if h1:
                t_words, h_words = set(words(core)), set(words(h1))
                if t_words and h_words and not (t_words & h_words):
                    findings["title_h1_mismatch"].append(
                        {"page": url, "title": title, "h1": h1})

        # Description checks
        if desc:
            n = len(desc)
            entry = {"page": url, "description": desc, "length": n}
            if n > DESC_MAX:
                findings["description_too_long"].append(entry)
                bands["description"]["too_long"] += 1
            elif n < DESC_MIN:
                findings["description_too_short"].append(entry)
                bands["description"]["too_short"] += 1
            else:
                bands["description"]["good"] += 1

            if title and desc.lower().strip(" .") == title.lower().strip(" ."):
                findings["description_duplicates_title"].append(
                    {"page": url, "value": desc})

            if not noindex or args.include_noindex:
                key = " ".join(desc.lower().split())
                desc_groups[key].append(url)

    for value, urls in title_groups.items():
        if len(urls) > 1:
            findings["duplicate_titles"].append({"title": value, "pages": sorted(urls)})
    for value, urls in desc_groups.items():
        if len(urls) > 1:
            findings["duplicate_descriptions"].append({"description": value, "pages": sorted(urls)})

    severity = {
        "missing_title": "high", "missing_description": "high",
        "duplicate_titles": "high", "duplicate_descriptions": "high",
        "multiple_titles": "medium", "multiple_descriptions": "medium",
        "title_too_long": "medium", "title_too_short": "medium",
        "description_too_long": "medium", "description_too_short": "medium",
        "generic_title": "medium",
        "description_duplicates_title": "low", "keyword_stuffing": "low",
        "title_h1_mismatch": "info",
    }
    summary = {
        "pages_analyzed": sum(1 for p in pages.values() if p.get("status", 200) == 200),
        "titles_found": sum(len(p.get("titles", [])) for p in pages.values()),
        "descriptions_found": sum(len(p.get("descriptions", [])) for p in pages.values()),
        "length_bands": {k: dict(v) for k, v in bands.items()},
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
