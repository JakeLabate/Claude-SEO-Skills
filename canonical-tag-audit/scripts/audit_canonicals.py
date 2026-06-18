#!/usr/bin/env python3
"""Audit a canonical inventory (from extract_canonicals.py) and emit findings.

Usage:
    python3 audit_canonicals.py canonical_inventory.json [--output audit_report.json]

Checks (see references/audit-checks.md):
- missing_canonical (high): indexable 200 HTML page with no canonical at all
- multiple_canonicals (high): more than one distinct canonical URL on a page
- canonical_to_non200 (high): canonical target returns 4xx/5xx/error
- canonical_to_redirect (high): canonical points at a URL that redirects
- canonical_to_noindex (medium): canonical points at a noindexed URL
- relative_canonical (medium): canonical href is not an absolute URL
- cross_host_canonical (medium): canonical points to a different host
- protocol_downgrade_canonical (medium): https page canonicalizes to http
- header_html_canonical_conflict (medium): Link header and HTML canonical disagree
- canonical_with_fragment (low): canonical URL contains a #fragment
- non_self_canonical (info): page canonicalizes to a different URL (note, not error)

Uses only the Python standard library.
"""

import argparse
import json
import sys
import urllib.parse


def host_of(url):
    h = urllib.parse.urlparse(url).netloc.lower()
    return h[4:] if h.startswith("www.") else h


def is_absolute(href):
    return bool(urllib.parse.urlparse(href).scheme)


def main():
    ap = argparse.ArgumentParser(description="Run canonical-tag audit checks.")
    ap.add_argument("inventory")
    ap.add_argument("--output", default="audit_report.json")
    args = ap.parse_args()

    with open(args.inventory, encoding="utf-8") as f:
        data = json.load(f)
    pages = data.get("pages", {})
    targets = data.get("targets", {})

    findings = {k: [] for k in (
        "missing_canonical", "multiple_canonicals", "canonical_to_non200",
        "canonical_to_redirect", "canonical_to_noindex", "relative_canonical",
        "cross_host_canonical", "protocol_downgrade_canonical",
        "header_html_canonical_conflict", "canonical_with_fragment",
        "non_self_canonical")}

    for url, page in pages.items():
        if page.get("status", 0) != 200:
            continue
        is_noindex = "noindex" in (page.get("meta_robots") or "").lower() or \
                     "noindex" in (page.get("x_robots") or "").lower()
        cans = page.get("canonicals", [])
        resolved = sorted({c["resolved"] for c in cans})
        final_url = page.get("final_url", url)

        if not cans and not page.get("header_canonical"):
            if not is_noindex:
                findings["missing_canonical"].append({"page": url})
            continue

        if len(resolved) > 1:
            findings["multiple_canonicals"].append({"page": url, "canonicals": resolved})

        header_can = page.get("header_canonical")
        if header_can and resolved and header_can not in resolved:
            findings["header_html_canonical_conflict"].append(
                {"page": url, "header": header_can, "html": resolved})

        for c in cans:
            raw, target = c["raw"], c["resolved"]
            if not is_absolute(raw):
                findings["relative_canonical"].append({"page": url, "raw": raw, "resolved": target})
            if urllib.parse.urldefrag(target)[1]:
                findings["canonical_with_fragment"].append({"page": url, "canonical": target})
            if host_of(target) != host_of(final_url):
                findings["cross_host_canonical"].append({"page": url, "canonical": target})
            if final_url.startswith("https://") and target.startswith("http://"):
                findings["protocol_downgrade_canonical"].append({"page": url, "canonical": target})
            if urllib.parse.urldefrag(target)[0].rstrip("/") != \
               urllib.parse.urldefrag(final_url)[0].rstrip("/"):
                findings["non_self_canonical"].append({"page": url, "canonical": target})

            t = targets.get(target)
            if t:
                if t["status"] == 0 or t["status"] >= 400:
                    findings["canonical_to_non200"].append(
                        {"page": url, "canonical": target, "status": t["status"]})
                elif t["redirects_to"]:
                    findings["canonical_to_redirect"].append(
                        {"page": url, "canonical": target, "redirects_to": t["redirects_to"]})
                if t["noindex"]:
                    findings["canonical_to_noindex"].append({"page": url, "canonical": target})

    severity = {
        "missing_canonical": "high", "multiple_canonicals": "high",
        "canonical_to_non200": "high", "canonical_to_redirect": "high",
        "canonical_to_noindex": "medium", "relative_canonical": "medium",
        "cross_host_canonical": "medium", "protocol_downgrade_canonical": "medium",
        "header_html_canonical_conflict": "medium",
        "canonical_with_fragment": "low", "non_self_canonical": "info",
    }
    summary = {
        "pages_analyzed": sum(1 for p in pages.values() if p.get("status", 0) == 200),
        "canonical_targets_probed": len(targets),
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
