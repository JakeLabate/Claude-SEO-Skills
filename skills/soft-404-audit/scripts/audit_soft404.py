#!/usr/bin/env python3
"""Audit a soft-404 inventory (from extract_pages.py) and emit findings.

Usage:
    python3 audit_soft404.py soft404_inventory.json [--output audit_report.json]
        [--thin-words 50]

Checks (see references/audit-checks.md):
- soft_404 (high): HTTP 200 page whose title/H1 contains a "not found"/error phrase
- missing_returns_200 (high): the missing-page probe returned 200 instead of 404/410
  (the site serves a soft 404 for every unknown URL)
- thin_error_page (medium): HTTP 200 page that is both very thin AND matches the
  missing-page probe's fingerprint (title/word count) — likely a masked error page
- empty_page (low): HTTP 200 page with almost no visible text and no error phrase

Uses only the Python standard library.
"""

import argparse
import json
import sys


def main():
    ap = argparse.ArgumentParser(description="Run soft-404 audit checks.")
    ap.add_argument("inventory")
    ap.add_argument("--output", default="audit_report.json")
    ap.add_argument("--thin-words", type=int, default=50,
                    help="word count below which a 200 page counts as thin")
    args = ap.parse_args()

    with open(args.inventory, encoding="utf-8") as f:
        data = json.load(f)
    pages = data.get("pages", {})
    probe = data.get("missing_probe") or {}

    findings = {k: [] for k in (
        "soft_404", "missing_returns_200", "thin_error_page", "empty_page")}

    probe_is_soft = probe.get("status") == 200
    probe_title = (probe.get("title") or "").strip().lower()
    probe_words = probe.get("word_count", 0)

    if probe_is_soft:
        findings["missing_returns_200"].append({
            "probe_url": probe.get("url"),
            "status": probe.get("status"),
            "note": "A non-existent URL returned 200 — the site serves a soft 404 "
                    "for unknown URLs instead of a real 404/410."})

    for url, page in pages.items():
        if page.get("status", 0) != 200:
            continue
        title = (page.get("title") or "").strip().lower()
        words = page.get("word_count", 0)
        has_error_phrase = page.get("error_phrase_in_title_or_h1", False)

        if has_error_phrase:
            findings["soft_404"].append(
                {"page": url, "title": page.get("title"), "h1": page.get("h1"),
                 "word_count": words})
            continue

        # Matches the missing-page probe's fingerprint (same title, similarly thin).
        if probe_is_soft and probe_title and title == probe_title and words <= max(probe_words, args.thin_words):
            findings["thin_error_page"].append(
                {"page": url, "title": page.get("title"), "word_count": words,
                 "matches": "missing-page probe"})
            continue

        if words < args.thin_words:
            findings["empty_page"].append(
                {"page": url, "title": page.get("title"), "word_count": words})

    severity = {
        "soft_404": "high", "missing_returns_200": "high",
        "thin_error_page": "medium", "empty_page": "low",
    }
    summary = {
        "pages_analyzed": sum(1 for p in pages.values() if p.get("status", 0) == 200),
        "missing_probe_status": probe.get("status"),
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
