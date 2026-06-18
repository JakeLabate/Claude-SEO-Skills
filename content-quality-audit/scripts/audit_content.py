#!/usr/bin/env python3
"""Audit a content inventory (from extract_content.py) and emit findings.

Usage:
    python3 audit_content.py content_inventory.json [--output audit_report.json]
        [--thin-words 300] [--similarity 0.85]

Checks (see references/audit-checks.md):
- thin_content (high): indexable page well under the word-count threshold
- duplicate_content (high): two or more indexable pages with identical body text
- near_duplicate_content (medium): pages whose MinHash similarity exceeds the
  threshold (templated/boilerplate pages with little unique text)
- low_text_to_html_ratio (medium): page is mostly markup, little text
- missing_h1 (low): indexable page with no H1 to frame the content

Near-duplicate detection uses the 32-value MinHash signatures from the collector,
so it is O(n^2) over small fixed-size signatures — fast and dependency-free.

Uses only the Python standard library.
"""

import argparse
import json
import sys
from collections import defaultdict


def mh_similarity(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(1 for x, y in zip(a, b) if x == y) / len(a)


def main():
    ap = argparse.ArgumentParser(description="Run content-quality audit checks.")
    ap.add_argument("inventory")
    ap.add_argument("--output", default="audit_report.json")
    ap.add_argument("--thin-words", type=int, default=300)
    ap.add_argument("--similarity", type=float, default=0.85,
                    help="MinHash similarity above which pages are near-duplicates")
    ap.add_argument("--min-ratio", type=float, default=0.1,
                    help="text-to-HTML ratio below which a page is mostly markup")
    args = ap.parse_args()

    with open(args.inventory, encoding="utf-8") as f:
        data = json.load(f)
    pages = data.get("pages", {})

    findings = {k: [] for k in (
        "thin_content", "duplicate_content", "near_duplicate_content",
        "low_text_to_html_ratio", "missing_h1")}

    indexable = {u: p for u, p in pages.items()
                 if p.get("status", 0) == 200 and not p.get("noindex")}

    # Exact duplicates by content hash.
    hash_groups = defaultdict(list)
    for url, p in indexable.items():
        if p.get("content_hash"):
            hash_groups[p["content_hash"]].append(url)
    exact_dupe_urls = set()
    for h, urls in hash_groups.items():
        if len(urls) > 1:
            findings["duplicate_content"].append(
                {"pages": sorted(urls), "word_count": indexable[urls[0]].get("word_count")})
            exact_dupe_urls.update(urls)

    # Per-page checks.
    for url, p in indexable.items():
        wc = p.get("word_count", 0)
        if wc < args.thin_words:
            findings["thin_content"].append(
                {"page": url, "word_count": wc, "title": p.get("title")})
        if 0 < p.get("text_to_html_ratio", 0) < args.min_ratio:
            findings["low_text_to_html_ratio"].append(
                {"page": url, "ratio": p.get("text_to_html_ratio"), "word_count": wc})
        if not p.get("h1"):
            findings["missing_h1"].append({"page": url, "title": p.get("title")})

    # Near-duplicates via MinHash (skip pages already flagged as exact dupes).
    items = [(u, p["minhash"]) for u, p in indexable.items()
             if p.get("minhash") and u not in exact_dupe_urls]
    seen_pairs = set()
    for i in range(len(items)):
        ui, si = items[i]
        for j in range(i + 1, len(items)):
            uj, sj = items[j]
            sim = mh_similarity(si, sj)
            if sim >= args.similarity:
                key = tuple(sorted((ui, uj)))
                if key not in seen_pairs:
                    seen_pairs.add(key)
                    findings["near_duplicate_content"].append(
                        {"pages": list(key), "similarity": round(sim, 2)})

    severity = {
        "thin_content": "high", "duplicate_content": "high",
        "near_duplicate_content": "medium", "low_text_to_html_ratio": "medium",
        "missing_h1": "low",
    }
    word_counts = [p.get("word_count", 0) for p in indexable.values()]
    summary = {
        "pages_analyzed": len(indexable),
        "median_word_count": sorted(word_counts)[len(word_counts) // 2] if word_counts else 0,
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
