#!/usr/bin/env python3
"""Fetch and parse a site's robots.txt, then probe its sitemap and resource references into a JSON inventory.

Usage:
    python3 collect_robots.py https://example.com [--output robots_inventory.json]
    python3 collect_robots.py https://example.com/robots.txt --robots [--output robots_inventory.json]

It fetches /robots.txt (without auto-following redirects, so a redirected or
HTML-served file is visible), records HTTP status, content type, byte size, gzip,
and a BOM flag, then parses it into user-agent groups, Sitemap: directives,
comments, unknown/unsupported directives, and per-line syntax errors. It probes
every declared Sitemap: URL for status, and fetches the homepage to extract
same-host CSS/JS/image resources and test each one against the '*' group's rules
so resources blocked from crawling can be flagged.

Output JSON schema:
{
  "site": "https://example.com",
  "robots_url": "https://example.com/robots.txt",
  "fetch": {"found": true, "status": 200, "content_type": "text/plain",
            "bytes": 1234, "gzip": false, "has_bom": false,
            "redirected": false, "final_url": "...", "looks_like_html": false},
  "raw": "<full robots.txt text>",
  "groups": [{"agents": ["*"], "disallow": ["/admin"], "allow": ["/admin/public"],
              "crawl_delay": null, "other": []}],
  "sitemaps": [{"url": "...", "absolute": true, "status": 200}],
  "comments": 3,
  "unknown_directives": [{"line": 12, "field": "noindex", "value": "/x"}],
  "line_errors": [{"line": 4, "text": "...", "error": "missing colon"}],
  "has_star_group": true,
  "sitewide_block_agents": ["*"],
  "resources": [{"url": "...", "type": "css", "path": "/a.css", "blocked": false}]
}

Uses only the Python standard library.
"""

import argparse
import gzip
import io
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

USER_AGENT = "RobotsAuditBot/1.0 (+claude-skill)"
TIMEOUT = 15
KNOWN_FIELDS = {"user-agent", "disallow", "allow", "sitemap", "crawl-delay", "host", "clean-param"}


class ResourceParser(HTMLParser):
    """Extract same-host CSS / JS / image resource URLs from a page."""

    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.resources = []

    def _add(self, kind, href):
        if href:
            self.resources.append((kind, urllib.parse.urljoin(self.base_url, href.strip())))

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "link" and "stylesheet" in (a.get("rel") or "").lower():
            self._add("css", a.get("href"))
        elif tag == "script" and a.get("src"):
            self._add("js", a.get("src"))
        elif tag == "img" and a.get("src"):
            self._add("img", a.get("src"))


def norm_host(host):
    host = host.lower()
    return host[4:] if host.startswith("www.") else host


def raw_get(url, max_bytes=10_000_000):
    """Plain GET (auto-follows redirects). Returns (status, final_url, raw_bytes, headers)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, resp.geturl(), resp.read(max_bytes), resp.headers
    except urllib.error.HTTPError as e:
        return e.code, url, b"", (e.headers if e.headers else None)
    except Exception:
        return 0, url, b"", None


def fetch_no_follow(url, max_bytes=2_000_000):
    """Fetch without following redirects. Returns (status, location, raw_bytes, headers)."""

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with opener.open(req, timeout=TIMEOUT) as resp:
            return resp.status, None, resp.read(max_bytes), resp.headers
    except urllib.error.HTTPError as e:
        loc = e.headers.get("Location") if e.headers else None
        return e.code, loc, b"", (e.headers if e.headers else None)
    except Exception:
        return 0, None, b"", None


def decode_body(raw, url, headers):
    """Return (text, is_gzip), handling gzip by header, .gz extension, or magic bytes."""
    is_gzip = url.lower().endswith(".gz")
    if headers is not None and "gzip" in (headers.get("Content-Encoding", "") or "").lower():
        is_gzip = True
    if raw[:2] == b"\x1f\x8b":
        is_gzip = True
    if is_gzip:
        try:
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        except Exception:
            pass
    return raw.decode("utf-8", errors="replace"), is_gzip


def parse_robots(text):
    """Parse robots.txt into groups, sitemaps, comments, unknown directives, and line errors."""
    groups, sitemaps, comments = [], [], 0
    unknown, errors = [], []
    current, last_directive = None, False
    for i, raw_line in enumerate(text.splitlines(), 1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            comments += 1
            continue
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            comments += 1
            continue
        if ":" not in line:
            errors.append({"line": i, "text": raw_line, "error": "missing colon"})
            continue
        field, _, value = line.partition(":")
        field, value = field.strip().lower(), value.strip()
        if field == "sitemap":
            if value:
                sitemaps.append(value)
            else:
                errors.append({"line": i, "text": raw_line, "error": "empty Sitemap value"})
        elif field == "user-agent":
            if current is None or last_directive:
                current = {"agents": [], "disallow": [], "allow": [],
                           "crawl_delay": None, "other": []}
                groups.append(current)
            if value:
                current["agents"].append(value)
            else:
                errors.append({"line": i, "text": raw_line, "error": "empty User-agent value"})
            last_directive = False
        elif field in ("disallow", "allow"):
            if current is None:
                errors.append({"line": i, "text": raw_line,
                               "error": f"{field} before any User-agent"})
            else:
                current[field].append(value)
                last_directive = True
        elif field == "crawl-delay":
            if current is not None:
                current["crawl_delay"] = value
                last_directive = True
        elif field in KNOWN_FIELDS:
            if current is not None:
                current["other"].append({"field": field, "value": value})
                last_directive = True
        else:
            unknown.append({"line": i, "field": field, "value": value})
    return {"groups": groups, "sitemaps": sitemaps, "comments": comments,
            "unknown": unknown, "errors": errors}


def robots_disallowed(path, groups):
    """True if the '*' user-agent group disallows the path (longest-match wins)."""
    star = [g for g in groups if "*" in g["agents"]]
    if not star:
        return False
    best_len, decision = -1, False
    for g in star:
        for rule, allow in [(d, False) for d in g["disallow"]] + [(a, True) for a in g["allow"]]:
            if rule == "":
                continue
            if path.startswith(rule) and len(rule) > best_len:
                best_len, decision = len(rule), allow
    return decision is False and best_len >= 0


def is_sitewide_block(group):
    """A group blocks the whole site if it disallows '/' and has no allow that re-opens root."""
    if "/" not in group["disallow"]:
        return False
    return not any(a == "/" for a in group["allow"])


def main():
    ap = argparse.ArgumentParser(description="Fetch, parse, and probe a site's robots.txt.")
    ap.add_argument("source", help="Site root URL, or a robots.txt URL with --robots")
    ap.add_argument("--robots", action="store_true", help="Treat source as a robots.txt URL directly")
    ap.add_argument("--no-resources", action="store_true",
                    help="skip homepage resource extraction / blocked-resource check")
    ap.add_argument("--output", default="robots_inventory.json")
    args = ap.parse_args()

    if args.robots:
        pu = urllib.parse.urlparse(args.source)
        site_root = f"{pu.scheme}://{pu.netloc}"
        robots_url = args.source
    else:
        site_root = args.source.rstrip("/")
        robots_url = site_root + "/robots.txt"

    status, location, raw, headers = fetch_no_follow(robots_url)
    redirected = 300 <= status < 400
    final_url = urllib.parse.urljoin(robots_url, location) if (redirected and location) else robots_url
    content_type = (headers.get("Content-Type", "") if headers else "") or ""
    has_bom = raw[:3] == b"\xef\xbb\xbf"
    text, is_gzip = decode_body(raw, robots_url, headers)
    if has_bom:
        text = text.lstrip("﻿")
    looks_like_html = "<html" in text[:2000].lower() or "<!doctype html" in text[:2000].lower()

    fetch = {
        "found": status == 200, "status": status, "content_type": content_type,
        "bytes": len(raw), "gzip": is_gzip, "has_bom": has_bom,
        "redirected": redirected, "final_url": final_url, "looks_like_html": looks_like_html,
    }
    print(f"robots.txt: [{status}] {robots_url} ({len(raw)} bytes)", file=sys.stderr)

    parsed = parse_robots(text) if (status == 200 and not looks_like_html) else {
        "groups": [], "sitemaps": [], "comments": 0, "unknown": [], "errors": []}

    # Probe declared sitemaps.
    site_host = norm_host(urllib.parse.urlparse(site_root).netloc)
    sitemaps = []
    for sm in parsed["sitemaps"]:
        absolute = bool(urllib.parse.urlparse(sm).scheme)
        entry = {"url": sm, "absolute": absolute, "status": None}
        if absolute:
            st, _f, _r, _h = raw_get(sm, max_bytes=2_000_000)
            entry["status"] = st
            print(f"  Sitemap [{st}] {sm}", file=sys.stderr)
        sitemaps.append(entry)

    groups = parsed["groups"]
    sitewide = [a for g in groups if is_sitewide_block(g) for a in g["agents"]]

    # Extract and test homepage resources.
    resources = []
    if not args.no_resources and status == 200 and not looks_like_html:
        hp_status, _f, hp_raw, hp_headers = raw_get(site_root, max_bytes=3_000_000)
        if hp_status == 200 and hp_raw:
            body, _g = decode_body(hp_raw, site_root, hp_headers)
            parser = ResourceParser(site_root)
            try:
                parser.feed(body)
            except Exception:
                pass
            seen = set()
            for kind, url in parser.resources:
                if url in seen:
                    continue
                seen.add(url)
                pu = urllib.parse.urlparse(url)
                if pu.netloc and norm_host(pu.netloc) != site_host:
                    continue  # only test same-host resources
                path = pu.path or "/"
                resources.append({"url": url, "type": kind, "path": path,
                                  "blocked": robots_disallowed(path, groups)})
            print(f"  Resources extracted: {len(resources)}", file=sys.stderr)

    out = {
        "site": site_root,
        "robots_url": robots_url,
        "fetch": fetch,
        "raw": text,
        "groups": groups,
        "sitemaps": sitemaps,
        "comments": parsed["comments"],
        "unknown_directives": parsed["unknown"],
        "line_errors": parsed["errors"],
        "has_star_group": any("*" in g["agents"] for g in groups),
        "sitewide_block_agents": sitewide,
        "resources": resources,
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(groups)} groups, {len(sitemaps)} sitemaps, "
          f"{len(resources)} resources to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
