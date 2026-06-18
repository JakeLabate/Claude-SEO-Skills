#!/usr/bin/env python3
"""Audit a pagination inventory (from extract_pagination.py) and emit findings.

Usage:
    python3 audit_pagination.py pagination_inventory.json [--output audit_report.json]

Checks (see references/audit-checks.md):
- paginated_canonical_to_page1 (high): page 2+ canonicalizes to page 1, hiding its
  content/links from the index (Google says each page should self-canonicalize)
- paginated_noindex (medium): a component (page 2+) page is noindexed
- paginated_missing_self_canonical (medium): page 2+ has no canonical at all
- rel_next_prev_broken (medium): a rel=next/prev target is non-200/redirects
- rel_next_prev_inconsistent (low): A's next is B but B's prev isn't A
- page1_has_page_param (low): the first page carries a redundant ?page=1
- rel_next_prev_present (info): Google no longer uses rel=next/prev for indexing

Uses only the Python standard library.
"""

import argparse
import json
import re
import sys
import urllib.parse

PAGE_PARAM_RE = re.compile(r'([?&])(?:page|p|pg|paged)=\d+', re.I)
PAGE_PATH_RE = re.compile(r'/(?:page|p)/\d+/?', re.I)


def strip_page(url):
    """Return the URL with its page-number component removed (i.e. the page-1 URL)."""
    if not url:
        return ""
    u = PAGE_PATH_RE.sub("/", url)
    u = PAGE_PARAM_RE.sub(lambda m: m.group(1), u)
    u = re.sub(r'[?&]$', '', u)
    return urllib.parse.urldefrag(u)[0].rstrip("/")


def norm(url):
    return urllib.parse.urldefrag(url)[0].rstrip("/") if url else ""


def main():
    ap = argparse.ArgumentParser(description="Run pagination audit checks.")
    ap.add_argument("inventory")
    ap.add_argument("--output", default="audit_report.json")
    args = ap.parse_args()

    with open(args.inventory, encoding="utf-8") as f:
        data = json.load(f)
    pages = data.get("pages", {})

    findings = {k: [] for k in (
        "paginated_canonical_to_page1", "paginated_noindex",
        "paginated_missing_self_canonical", "rel_next_prev_broken",
        "rel_next_prev_inconsistent", "page1_has_page_param",
        "rel_next_prev_present")}

    # index by normalized final URL for reciprocity + target status lookups
    by_url = {}
    for u, p in pages.items():
        by_url[norm(p.get("final_url", u))] = (u, p)

    for url, page in pages.items():
        if page.get("status", 0) != 200:
            continue
        pn = page.get("page_number")
        canonical = page.get("canonical")
        is_noindex = "noindex" in (page.get("meta_robots") or "").lower()
        rel_next, rel_prev = page.get("rel_next"), page.get("rel_prev")

        if rel_next or rel_prev:
            findings["rel_next_prev_present"].append(
                {"page": url, "next": rel_next, "prev": rel_prev})

        # Component pages (page 2+).
        if pn and pn >= 2:
            if is_noindex:
                findings["paginated_noindex"].append({"page": url, "page_number": pn})
            if not canonical:
                findings["paginated_missing_self_canonical"].append(
                    {"page": url, "page_number": pn})
            elif norm(canonical) == strip_page(page.get("final_url", url)) \
                    and norm(canonical) != norm(page.get("final_url", url)):
                findings["paginated_canonical_to_page1"].append(
                    {"page": url, "page_number": pn, "canonical": canonical})

        if pn == 1:
            findings["page1_has_page_param"].append({"page": url})

        # rel=next/prev target health + reciprocity.
        for rel, target in (("next", rel_next), ("prev", rel_prev)):
            if not target:
                continue
            t = by_url.get(norm(target))
            if t:
                _tu, tp = t
                if tp.get("status", 0) != 200:
                    findings["rel_next_prev_broken"].append(
                        {"page": url, "rel": rel, "target": target,
                         "status": tp.get("status")})
                back = tp.get("rel_prev") if rel == "next" else tp.get("rel_next")
                if back is not None and norm(back) != norm(page.get("final_url", url)):
                    findings["rel_next_prev_inconsistent"].append(
                        {"page": url, "rel": rel, "target": target,
                         "target_points_back_to": back})

    severity = {
        "paginated_canonical_to_page1": "high",
        "paginated_noindex": "medium", "paginated_missing_self_canonical": "medium",
        "rel_next_prev_broken": "medium",
        "rel_next_prev_inconsistent": "low", "page1_has_page_param": "low",
        "rel_next_prev_present": "info",
    }
    summary = {
        "pages_analyzed": sum(1 for p in pages.values() if p.get("status", 0) == 200),
        "paginated_pages": sum(1 for p in pages.values() if (p.get("page_number") or 0) >= 2),
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
