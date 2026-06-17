#!/usr/bin/env python3
"""Audit a sitemap inventory JSON (from collect_sitemap.py) and emit findings.

Usage:
    python3 audit_sitemap.py sitemap_inventory.json [--output audit_report.json]

Checks implemented (see references/audit-checks.md):
- no_sitemap_found: no parseable sitemap discovered (high)
- sitemap_not_in_robots: sitemaps exist but none are declared in robots.txt (medium)
- sitemap_parse_error / sitemap_fetch_error: a sitemap file is broken or unreachable (high)
- sitemap_too_many_urls (> 50,000) / sitemap_too_large (> 50MB uncompressed) (high)
- url_error: a listed URL returns 4xx/5xx/0 (high)
- url_redirects: a listed URL 3xx-redirects instead of being a final 200 (high)
- url_noindex: a listed URL is noindex via meta robots or X-Robots-Tag (high)
- url_robots_disallowed: a listed URL is blocked by robots.txt (high)
- url_canonicalized_away: a listed URL canonicalizes to a different URL (medium)
- url_wrong_host: a listed URL is on a different host/scheme than the site (medium)
- duplicate_urls: the same URL appears in more than one sitemap (low)
- missing_lastmod / invalid_lastmod / future_lastmod (low)
- invalid_priority / invalid_changefreq (low)

Uses only the Python standard library.
"""

import argparse
import datetime as dt
import json
import re
import sys
import urllib.parse

MAX_URLS_PER_SITEMAP = 50_000
MAX_BYTES_PER_SITEMAP = 50 * 1024 * 1024  # 50 MB uncompressed
VALID_CHANGEFREQ = {"always", "hourly", "daily", "weekly", "monthly", "yearly", "never"}
W3C_DATE_RE = re.compile(
    r"^\d{4}(-\d{2}(-\d{2}(T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})?)?)?)?$")


def norm_host(host):
    host = host.lower()
    return host[4:] if host.startswith("www.") else host


def norm(url):
    return urllib.parse.urldefrag((url or "").strip())[0].rstrip("/").lower()


def is_noindex(page):
    blob = ((page.get("meta_robots") or "") + " " + (page.get("x_robots_tag") or "")).lower()
    return "noindex" in blob or "none" in blob


def parse_lastmod(value):
    if not W3C_DATE_RE.match(value):
        return None, "invalid"
    try:
        date_part = value[:10]
        d = dt.date.fromisoformat(date_part)
        return d, None
    except ValueError:
        return None, "invalid"


def main():
    ap = argparse.ArgumentParser(description="Run sitemap audit checks.")
    ap.add_argument("inventory", help="sitemap_inventory.json from collect_sitemap.py")
    ap.add_argument("--output", default="audit_report.json")
    args = ap.parse_args()

    with open(args.inventory, encoding="utf-8") as f:
        data = json.load(f)

    site = data.get("site", "")
    site_host = norm_host(urllib.parse.urlparse(site).netloc)
    site_scheme = urllib.parse.urlparse(site).scheme or "https"
    robots = data.get("robots_txt", {})
    sitemaps = data.get("sitemaps", [])
    urls = data.get("urls", {})
    today = dt.date.today()

    findings = {
        "no_sitemap_found": [], "sitemap_not_in_robots": [],
        "sitemap_parse_error": [], "sitemap_fetch_error": [],
        "sitemap_too_many_urls": [], "sitemap_too_large": [],
        "url_error": [], "url_redirects": [], "url_noindex": [],
        "url_robots_disallowed": [], "url_canonicalized_away": [],
        "url_wrong_host": [], "duplicate_urls": [],
        "missing_lastmod": [], "invalid_lastmod": [], "future_lastmod": [],
        "invalid_priority": [], "invalid_changefreq": [],
    }

    parseable = [s for s in sitemaps if s.get("type") and not s.get("error")]
    if not parseable:
        findings["no_sitemap_found"].append({"checked": [s.get("url") for s in sitemaps] or "none"})

    if parseable and not robots.get("sitemaps"):
        findings["sitemap_not_in_robots"].append(
            {"robots_status": robots.get("status"),
             "sitemaps_found": [s["url"] for s in parseable]})

    for s in sitemaps:
        err = s.get("error")
        if err:
            if "parse" in err:
                findings["sitemap_parse_error"].append({"sitemap": s["url"], "error": err})
            else:
                findings["sitemap_fetch_error"].append({"sitemap": s["url"], "error": err})
        if s.get("type") == "urlset" and s.get("url_count", 0) > MAX_URLS_PER_SITEMAP:
            findings["sitemap_too_many_urls"].append(
                {"sitemap": s["url"], "url_count": s["url_count"]})
        if s.get("bytes", 0) > MAX_BYTES_PER_SITEMAP and not s.get("gzip"):
            findings["sitemap_too_large"].append({"sitemap": s["url"], "bytes": s["bytes"]})

    for loc, p in urls.items():
        status = p.get("status")
        if status is not None:  # probed
            if status == 0 or (status and status >= 400):
                findings["url_error"].append({"url": loc, "status": status})
            elif p.get("redirected"):
                findings["url_redirects"].append(
                    {"url": loc, "status": status, "final_url": p.get("final_url")})
            else:
                if is_noindex(p):
                    findings["url_noindex"].append(
                        {"url": loc, "meta_robots": p.get("meta_robots"),
                         "x_robots_tag": p.get("x_robots_tag")})
                canonical = p.get("canonical")
                if canonical and norm(canonical) != norm(loc):
                    findings["url_canonicalized_away"].append(
                        {"url": loc, "canonical": canonical})
            if p.get("robots_disallowed"):
                findings["url_robots_disallowed"].append({"url": loc})

        # Host / scheme correctness (independent of probing)
        pu = urllib.parse.urlparse(loc)
        if pu.netloc and norm_host(pu.netloc) != site_host:
            findings["url_wrong_host"].append({"url": loc, "expected_host": site_host})
        elif pu.scheme and pu.scheme != site_scheme:
            findings["url_wrong_host"].append(
                {"url": loc, "issue": f"scheme {pu.scheme}, expected {site_scheme}"})

        # lastmod / priority / changefreq hygiene
        lastmod = p.get("lastmod")
        if not lastmod:
            findings["missing_lastmod"].append({"url": loc})
        else:
            d, err = parse_lastmod(lastmod)
            if err:
                findings["invalid_lastmod"].append({"url": loc, "lastmod": lastmod})
            elif d and d > today:
                findings["future_lastmod"].append({"url": loc, "lastmod": lastmod})

        prio = p.get("priority")
        if prio is not None:
            try:
                if not (0.0 <= float(prio) <= 1.0):
                    raise ValueError
            except ValueError:
                findings["invalid_priority"].append({"url": loc, "priority": prio})

        cf = p.get("changefreq")
        if cf is not None and cf.lower() not in VALID_CHANGEFREQ:
            findings["invalid_changefreq"].append({"url": loc, "changefreq": cf})

    for loc in data.get("duplicate_urls", []):
        findings["duplicate_urls"].append(
            {"url": loc, "in_sitemaps": urls.get(loc, {}).get("in_sitemaps", [])})

    severity = {
        "no_sitemap_found": "high", "sitemap_parse_error": "high", "sitemap_fetch_error": "high",
        "sitemap_too_many_urls": "high", "sitemap_too_large": "high",
        "url_error": "high", "url_redirects": "high", "url_noindex": "high",
        "url_robots_disallowed": "high",
        "sitemap_not_in_robots": "medium", "url_canonicalized_away": "medium",
        "url_wrong_host": "medium",
        "duplicate_urls": "low", "missing_lastmod": "low", "invalid_lastmod": "low",
        "future_lastmod": "low", "invalid_priority": "low", "invalid_changefreq": "low",
    }
    probed = sum(1 for p in urls.values() if p.get("status") is not None)
    summary = {
        "sitemaps_found": len([s for s in sitemaps if s.get("type")]),
        "total_urls_listed": data.get("url_count", len(urls)),
        "urls_probed": probed,
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
