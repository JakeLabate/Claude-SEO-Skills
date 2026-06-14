#!/usr/bin/env python3
"""Audit a heading inventory JSON (from extract_headings.py) and emit audit findings.

Usage:
    python3 audit_headings.py heading_inventory.json [--output audit_report.json]
        [--long-heading 70]

Checks implemented (see references/audit-checks.md):
- missing_h1: page has no <h1> (high)
- no_headings: page has no headings at all (high)
- multiple_h1: page has more than one <h1> (medium)
- skipped_level: heading depth jumps down by more than one (e.g. h2 -> h4) (medium)
- empty_heading: a heading element with no text (medium)
- first_not_h1: the first heading on the page is not an <h1> (low)
- long_heading: heading longer than --long-heading characters (low)
- duplicate_heading: identical heading text repeated on one page (low)
- title_h1_mismatch: <h1> and <title> share no significant words (informational)

Uses only the Python standard library.
"""

import argparse
import json
import re
import sys
from collections import Counter

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in",
    "is", "it", "of", "on", "or", "the", "to", "with", "your", "you", "our",
}


def words(text):
    return [w for w in re.findall(r"[a-z0-9']+", (text or "").lower()) if w not in STOPWORDS]


def main():
    ap = argparse.ArgumentParser(description="Run heading-structure audit checks.")
    ap.add_argument("inventory", help="heading_inventory.json from extract_headings.py")
    ap.add_argument("--output", default="audit_report.json")
    ap.add_argument("--long-heading", type=int, default=70,
                    help="flag headings longer than this many characters (default 70)")
    args = ap.parse_args()

    with open(args.inventory, encoding="utf-8") as f:
        data = json.load(f)
    pages = data.get("pages", {})

    findings = {
        "missing_h1": [], "no_headings": [], "multiple_h1": [],
        "skipped_level": [], "empty_heading": [], "first_not_h1": [],
        "long_heading": [], "duplicate_heading": [], "title_h1_mismatch": [],
    }

    pages_analyzed = 0
    for url, page in pages.items():
        if page.get("status", 200) != 200:
            continue
        pages_analyzed += 1
        headings = page.get("headings", [])
        levels = [h["level"] for h in headings]
        h1s = [h for h in headings if h["level"] == 1]

        if not headings:
            findings["no_headings"].append({"page": url})
            continue

        if not h1s:
            findings["missing_h1"].append({"page": url})
        if len(h1s) > 1:
            findings["multiple_h1"].append(
                {"page": url, "count": len(h1s), "values": [h["text"] for h in h1s]})

        if headings[0]["level"] != 1:
            findings["first_not_h1"].append(
                {"page": url, "first_level": headings[0]["level"], "first_text": headings[0]["text"]})

        # Skipped levels: a descent of more than one between consecutive headings.
        prev = None
        for h in headings:
            if prev is not None and h["level"] > prev + 1:
                findings["skipped_level"].append(
                    {"page": url, "from": f"h{prev}", "to": f"h{h['level']}", "text": h["text"]})
            prev = h["level"]

        # Empty headings
        for h in headings:
            if not h["text"].strip():
                findings["empty_heading"].append({"page": url, "level": f"h{h['level']}"})

        # Long headings
        for h in headings:
            if len(h["text"]) > args.long_heading:
                findings["long_heading"].append(
                    {"page": url, "level": f"h{h['level']}", "text": h["text"], "length": len(h["text"])})

        # Duplicate heading text on the same page
        counts = Counter(h["text"].strip().lower() for h in headings if h["text"].strip())
        for text, c in counts.items():
            if c > 1:
                findings["duplicate_heading"].append({"page": url, "text": text, "count": c})

        # Title / H1 topical mismatch (informational)
        title = page.get("title")
        if h1s and title:
            h1_words, t_words = set(words(h1s[0]["text"])), set(words(title))
            if h1_words and t_words and not (h1_words & t_words):
                findings["title_h1_mismatch"].append(
                    {"page": url, "h1": h1s[0]["text"], "title": title})

    severity = {
        "missing_h1": "high", "no_headings": "high",
        "multiple_h1": "medium", "skipped_level": "medium", "empty_heading": "medium",
        "first_not_h1": "low", "long_heading": "low", "duplicate_heading": "low",
        "title_h1_mismatch": "info",
    }
    summary = {
        "pages_analyzed": pages_analyzed,
        "headings_found": sum(len(p.get("headings", [])) for p in pages.values()),
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
