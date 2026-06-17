#!/usr/bin/env python3
"""Audit a robots.txt inventory JSON (from collect_robots.py) and emit findings.

Usage:
    python3 audit_robots.py robots_inventory.json [--output audit_report.json]

Checks implemented (see references/audit-checks.md):
- robots_5xx: robots.txt returns 5xx (Google treats this as "disallow all") (high)
- robots_redirect: robots.txt redirects instead of returning the file directly (high)
- robots_served_as_html: robots.txt returns an HTML page, not plain text (high)
- sitewide_block: a User-agent group disallows the entire site with Disallow: / (high)
- syntax_error: malformed lines (missing colon, directive before User-agent, etc.) (high)
- file_too_large: robots.txt exceeds 500 KiB (Google ignores content past it) (high)
- blocked_resource: a CSS/JS/image needed to render the page is disallowed (medium)
- no_sitemap_directive: no Sitemap: directive present (medium)
- sitemap_unreachable: a declared Sitemap: URL is non-200 or not absolute (medium)
- no_star_group: no default User-agent: * group (medium)
- unsupported_directive: noindex/nofollow/crawl-delay etc. that Google ignores (medium/low)
- robots_404: robots.txt missing entirely (low — means "allow all", but worth a real file)
- duplicate_star_group: more than one User-agent: * group (low)
- has_bom: a UTF-8 BOM precedes the file (low)
- empty_disallow_confusion: Disallow: with no value (allows everything — often a mistake) (low)

Uses only the Python standard library.
"""

import argparse
import json
import sys

MAX_BYTES = 500 * 1024  # Google ignores robots.txt content past 500 KiB
RENDER_BLOCKING_TYPES = {"css", "js"}
# Directives that are not part of the robots.txt standard / are ignored by Google.
UNSUPPORTED_FIELDS = {"noindex", "nofollow", "crawl-delay", "host", "request-rate", "clean-param"}


def main():
    ap = argparse.ArgumentParser(description="Run robots.txt audit checks.")
    ap.add_argument("inventory", help="robots_inventory.json from collect_robots.py")
    ap.add_argument("--output", default="audit_report.json")
    args = ap.parse_args()

    with open(args.inventory, encoding="utf-8") as f:
        data = json.load(f)

    fetch = data.get("fetch", {})
    groups = data.get("groups", [])
    sitemaps = data.get("sitemaps", [])
    resources = data.get("resources", [])

    findings = {
        "robots_5xx": [], "robots_redirect": [], "robots_served_as_html": [],
        "sitewide_block": [], "syntax_error": [], "file_too_large": [],
        "blocked_resource": [], "no_sitemap_directive": [], "sitemap_unreachable": [],
        "no_star_group": [], "unsupported_directive": [],
        "robots_404": [], "duplicate_star_group": [], "has_bom": [],
        "empty_disallow_confusion": [],
    }

    status = fetch.get("status")
    if status and 500 <= status < 600:
        findings["robots_5xx"].append({"status": status, "url": data.get("robots_url")})
    if fetch.get("redirected"):
        findings["robots_redirect"].append(
            {"status": status, "final_url": fetch.get("final_url")})
    if fetch.get("looks_like_html"):
        findings["robots_served_as_html"].append(
            {"content_type": fetch.get("content_type")})
    if status == 404 or (status == 0):
        findings["robots_404"].append({"status": status, "url": data.get("robots_url")})

    if fetch.get("bytes", 0) > MAX_BYTES:
        findings["file_too_large"].append({"bytes": fetch.get("bytes"), "limit": MAX_BYTES})
    if fetch.get("has_bom"):
        findings["has_bom"].append({"note": "UTF-8 BOM precedes the file"})

    for agent in data.get("sitewide_block_agents", []):
        findings["sitewide_block"].append({"agent": agent, "rule": "Disallow: /"})

    for err in data.get("line_errors", []):
        findings["syntax_error"].append(err)

    # Resource blocking.
    for r in resources:
        if r.get("blocked") and r.get("type") in RENDER_BLOCKING_TYPES:
            findings["blocked_resource"].append(
                {"url": r["url"], "type": r["type"], "path": r["path"]})

    # Sitemap directives.
    if not sitemaps:
        findings["no_sitemap_directive"].append({"note": "no Sitemap: directive in robots.txt"})
    for sm in sitemaps:
        if not sm.get("absolute"):
            findings["sitemap_unreachable"].append(
                {"url": sm["url"], "issue": "not an absolute URL"})
        elif sm.get("status") not in (200, None):
            findings["sitemap_unreachable"].append(
                {"url": sm["url"], "status": sm.get("status")})

    # Group structure.
    star_groups = [g for g in groups if "*" in g.get("agents", [])]
    if groups and not star_groups:
        findings["no_star_group"].append(
            {"note": "no default User-agent: * group; unlisted crawlers get no rules"})
    if len(star_groups) > 1:
        findings["duplicate_star_group"].append({"count": len(star_groups)})

    # Unsupported directives + empty Disallow.
    for u in data.get("unknown_directives", []):
        if u.get("field") in UNSUPPORTED_FIELDS:
            findings["unsupported_directive"].append(u)
    for g in groups:
        if g.get("crawl_delay") is not None:
            findings["unsupported_directive"].append(
                {"field": "crawl-delay", "value": g["crawl_delay"], "agents": g["agents"]})
        for o in g.get("other", []):
            if o.get("field") in UNSUPPORTED_FIELDS:
                findings["unsupported_directive"].append({**o, "agents": g["agents"]})
        # An explicit empty Disallow allows everything; flag only when it coexists with
        # real Disallow rules in the same group (a likely mistake / no-op leftover).
        if "" in g.get("disallow", []) and any(d for d in g.get("disallow", [])):
            findings["empty_disallow_confusion"].append({"agents": g["agents"]})

    severity = {
        "robots_5xx": "high", "robots_redirect": "high", "robots_served_as_html": "high",
        "sitewide_block": "high", "syntax_error": "high", "file_too_large": "high",
        "blocked_resource": "medium", "no_sitemap_directive": "medium",
        "sitemap_unreachable": "medium", "no_star_group": "medium",
        "unsupported_directive": "medium",
        "robots_404": "low", "duplicate_star_group": "low", "has_bom": "low",
        "empty_disallow_confusion": "low",
    }
    summary = {
        "robots_status": status,
        "groups": len(groups),
        "sitemaps_declared": len(sitemaps),
        "resources_checked": len(resources),
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
