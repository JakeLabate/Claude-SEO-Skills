#!/usr/bin/env python3
"""Audit an llms.txt inventory JSON (from collect_llms.py) and emit findings.

Usage:
    python3 audit_llms.py llms_inventory.json [--output audit_report.json]

Checks implemented (see references/audit-checks.md):
- no_llms_txt: /llms.txt is missing (non-200) (high)
- served_as_html: /llms.txt returns an HTML page, not markdown/plain text (high)
- missing_h1: no top-level H1 title — the one required element (high)
- link_error: a referenced link returns 4xx/5xx/error (high)
- llms_redirect: /llms.txt itself redirects instead of returning the file (medium)
- link_redirects: a referenced link 3xx-redirects instead of being a final 200 (medium)
- missing_summary: no blockquote summary after the H1 (medium)
- link_missing_description: a list link has no description (medium)
- malformed_list_item: a list item under a section is not a proper markdown link (medium)
- link_wrong_host: a referenced link is on a different host (medium)
- link_noindex_or_blocked: a referenced page is noindex or blocked by robots.txt (medium)
- wrong_content_type: not served as text/markdown or text/plain (medium)
- relative_link: a link uses a relative URL instead of an absolute one (low)
- no_sections: no H2 sections / no links at all (low)
- duplicate_link: the same URL is listed more than once (low)
- llms_full_txt_missing: /llms-full.txt is not present (low, informational)

Uses only the Python standard library.
"""

import argparse
import json
import sys
import urllib.parse

MARKDOWN_TYPES = ("text/markdown", "text/plain", "text/x-markdown")


def norm_host(host):
    host = host.lower()
    return host[4:] if host.startswith("www.") else host


def is_noindex(page):
    blob = ((page.get("meta_robots") or "") + " " + (page.get("x_robots_tag") or "")).lower()
    return "noindex" in blob or "none" in blob


def main():
    ap = argparse.ArgumentParser(description="Run llms.txt audit checks.")
    ap.add_argument("inventory", help="llms_inventory.json from collect_llms.py")
    ap.add_argument("--output", default="audit_report.json")
    args = ap.parse_args()

    with open(args.inventory, encoding="utf-8") as f:
        data = json.load(f)

    site = data.get("site", "")
    site_host = norm_host(urllib.parse.urlparse(site).netloc)
    fetch = data.get("fetch", {})
    sections = data.get("sections", [])
    links = data.get("links", {})

    findings = {
        "no_llms_txt": [], "served_as_html": [], "missing_h1": [], "link_error": [],
        "llms_redirect": [], "link_redirects": [], "missing_summary": [],
        "link_missing_description": [], "malformed_list_item": [], "link_wrong_host": [],
        "link_noindex_or_blocked": [], "wrong_content_type": [],
        "relative_link": [], "no_sections": [], "duplicate_link": [],
        "llms_full_txt_missing": [],
    }

    status = fetch.get("status")
    available = status == 200 and not fetch.get("looks_like_html")

    if status != 200:
        findings["no_llms_txt"].append({"status": status, "url": data.get("llms_url")})
    if fetch.get("looks_like_html"):
        findings["served_as_html"].append({"content_type": fetch.get("content_type")})
    if fetch.get("redirected"):
        findings["llms_redirect"].append(
            {"status": status, "final_url": fetch.get("final_url")})

    if available:
        ctype = (fetch.get("content_type") or "").lower()
        if ctype and not any(t in ctype for t in MARKDOWN_TYPES):
            findings["wrong_content_type"].append({"content_type": fetch.get("content_type")})

        if not data.get("h1"):
            findings["missing_h1"].append({"note": "no top-level '# Title' heading"})
        if not data.get("summary"):
            findings["missing_summary"].append({"note": "no '> summary' blockquote after the H1"})

        has_links = any(item.get("is_link") for s in sections for item in s["items"])
        if not sections or not has_links:
            findings["no_sections"].append(
                {"sections": len(sections), "note": "no H2 sections with links"})

        # List-item structure.
        for sec in sections:
            for item in sec["items"]:
                if not item.get("is_link"):
                    findings["malformed_list_item"].append(
                        {"section": sec["heading"], "text": item.get("raw")})
                    continue
                if not item.get("description"):
                    findings["link_missing_description"].append(
                        {"section": sec["heading"], "url": item.get("url"),
                         "title": item.get("title")})
                if item.get("relative"):
                    findings["relative_link"].append(
                        {"section": sec["heading"], "url": item.get("url")})

    # Per-link probe results.
    for url, p in links.items():
        st = p.get("status")
        if st is not None:
            if st == 0 or (st and st >= 400):
                findings["link_error"].append({"url": url, "status": st})
            elif p.get("redirected"):
                findings["link_redirects"].append(
                    {"url": url, "status": st, "final_url": p.get("final_url")})
            else:
                if is_noindex(p) or p.get("robots_disallowed"):
                    findings["link_noindex_or_blocked"].append(
                        {"url": url, "noindex": is_noindex(p),
                         "robots_disallowed": p.get("robots_disallowed")})
        pu = urllib.parse.urlparse(url)
        if pu.netloc and norm_host(pu.netloc) != site_host:
            findings["link_wrong_host"].append({"url": url, "expected_host": site_host})

    # Duplicate links across sections.
    for url, p in links.items():
        if len(p.get("sections", [])) > 1:
            findings["duplicate_link"].append({"url": url, "sections": p["sections"]})

    full = data.get("llms_full_txt", {})
    if not full.get("found"):
        findings["llms_full_txt_missing"].append(
            {"checked": full.get("checked"), "status": full.get("status")})

    severity = {
        "no_llms_txt": "high", "served_as_html": "high", "missing_h1": "high",
        "link_error": "high",
        "llms_redirect": "medium", "link_redirects": "medium", "missing_summary": "medium",
        "link_missing_description": "medium", "malformed_list_item": "medium",
        "link_wrong_host": "medium", "link_noindex_or_blocked": "medium",
        "wrong_content_type": "medium",
        "relative_link": "low", "no_sections": "low", "duplicate_link": "low",
        "llms_full_txt_missing": "low",
    }
    probed = sum(1 for p in links.values() if p.get("status") is not None)
    summary = {
        "llms_txt_status": status,
        "h1": data.get("h1"),
        "sections": len(sections),
        "links_found": len(links),
        "links_probed": probed,
        "llms_full_txt_found": full.get("found", False),
        "issues_by_check": {k: len(v) for k, v in findings.items()},
        "issues_by_severity": {
            level: sum(len(findings[k]) for k, s in severity.items() if s == level)
            for level in ("high", "medium", "low")
        },
    }
    report = {"summary": summary, "severity": severity, "findings": findings}

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(json.dumps(summary, indent=2))
    print(f"Full report written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
