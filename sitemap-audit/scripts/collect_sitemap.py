#!/usr/bin/env python3
"""Discover and parse a site's XML sitemaps, then probe every listed URL into a JSON inventory.

Usage:
    python3 collect_sitemap.py https://example.com [--max-urls 2000] [--output sitemap_inventory.json]
    python3 collect_sitemap.py https://example.com/sitemap.xml --sitemap [--max-urls 2000] [--output sitemap_inventory.json]

Discovery order (for the site-root form):
1. Sitemap: directives in /robots.txt
2. /sitemap.xml and /sitemap_index.xml fallbacks

For each sitemap file it records type (index/urlset), URL count, byte size, gzip,
HTTP status, and XML parse errors. For each listed URL it records lastmod /
changefreq / priority from the sitemap, then fetches the URL (without auto-follow
beyond one resolution) to capture status, redirect target, canonical, meta robots,
and the X-Robots-Tag header — everything needed to flag URLs that should not be in
a sitemap (non-200, redirecting, noindex, canonicalized away, blocked by robots).

Output JSON schema:
{
  "site": "https://example.com",
  "robots_txt": {"found": true, "status": 200, "sitemaps": [...], "rules": [...]},
  "sitemaps": [{"url": "...", "type": "urlset|sitemapindex", "status": 200,
                "url_count": 120, "bytes": 34567, "gzip": false, "error": null}],
  "url_count": 120,
  "duplicate_urls": ["..."],
  "urls": {
    "<loc>": {
      "lastmod": "...|null", "changefreq": "...|null", "priority": "...|null",
      "in_sitemaps": ["..."],
      "status": 200, "redirected": false, "final_url": "...",
      "canonical": "...|null", "meta_robots": "...|null", "x_robots_tag": "...|null",
      "robots_disallowed": false
    }
  }
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
import xml.etree.ElementTree as ET
from collections import deque
from html.parser import HTMLParser

USER_AGENT = "SitemapAuditBot/1.0 (+claude-skill)"
TIMEOUT = 15
SM_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
MAX_SITEMAPS = 100


class PageHeadParser(HTMLParser):
    """Extract canonical and meta robots only."""

    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.canonical = None
        self.meta_robots = None
        self._body_started = False

    def handle_starttag(self, tag, attrs):
        if tag == "body":
            self._body_started = True
        if self._body_started:
            return
        a = dict(attrs)
        if tag == "link" and (a.get("rel") or "").lower() == "canonical" and a.get("href"):
            self.canonical = urllib.parse.urljoin(self.base_url, a["href"].strip())
        elif tag == "meta" and (a.get("name") or "").lower() == "robots":
            self.meta_robots = a.get("content")


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


def fetch_no_follow(url):
    """Fetch without following redirects. Returns (status, location, body, headers)."""

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with opener.open(req, timeout=TIMEOUT) as resp:
            ctype = resp.headers.get("Content-Type", "")
            body = resp.read(2_000_000).decode("utf-8", errors="replace") if "html" in ctype else None
            return resp.status, None, body, resp.headers
    except urllib.error.HTTPError as e:
        loc = e.headers.get("Location") if e.headers else None
        return e.code, loc, None, (e.headers if e.headers else None)
    except Exception:
        return 0, None, None, None


def decode_body(raw, url, headers):
    """Return decoded text, handling gzip (by header, .gz extension, or magic bytes)."""
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
    groups, sitemaps, current, last_directive = [], [], None, False
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, _, value = line.partition(":")
        field, value = field.strip().lower(), value.strip()
        if field == "sitemap":
            if value:
                sitemaps.append(value)
        elif field == "user-agent":
            if current is None or last_directive:
                current = {"agents": [], "disallow": [], "allow": []}
                groups.append(current)
            current["agents"].append(value)
            last_directive = False
        elif field in ("disallow", "allow") and current is not None:
            current[field].append(value)
            last_directive = True
    flat = []
    for g in groups:
        for agent in g["agents"]:
            flat.append({"agent": agent, "disallow": list(g["disallow"]), "allow": list(g["allow"])})
    return flat, sitemaps


def fetch_robots(site_root):
    status, _f, raw, _h = raw_get(site_root.rstrip("/") + "/robots.txt", max_bytes=1_000_000)
    if status != 200:
        return {"found": False, "status": status, "sitemaps": [], "rules": []}
    rules, sitemaps = parse_robots(raw.decode("utf-8", errors="replace"))
    return {"found": True, "status": status, "sitemaps": sitemaps, "rules": rules}


def robots_disallowed(path, rules):
    """True if the '*' user-agent group disallows the path (longest-match wins)."""
    star = [r for r in rules if r["agent"] == "*"]
    if not star:
        return False
    best_len, decision = -1, False
    for r in star:
        for rule, allow in [(d, False) for d in r["disallow"]] + [(a, True) for a in r["allow"]]:
            if rule == "":
                continue
            if path.startswith(rule) and len(rule) > best_len:
                best_len, decision = len(rule), allow
    return decision is False and best_len >= 0


def collect_sitemaps(seeds, max_sitemaps):
    """Follow sitemap indexes; return (sitemap_meta, {loc: {lastmod,changefreq,priority,in_sitemaps}})."""
    sitemap_meta = []
    url_entries = {}
    queue = deque(seeds)
    seen = set()
    while queue and len(seen) < max_sitemaps:
        sm = queue.popleft()
        if sm in seen:
            continue
        seen.add(sm)
        status, _f, raw, headers = raw_get(sm)
        meta = {"url": sm, "type": None, "status": status, "url_count": 0,
                "bytes": len(raw), "gzip": False, "error": None}
        if status != 200 or not raw:
            meta["error"] = f"status {status}"
            sitemap_meta.append(meta)
            continue
        text, is_gzip = decode_body(raw, sm, headers)
        meta["gzip"] = is_gzip
        try:
            root = ET.fromstring(text)
        except ET.ParseError as e:
            meta["error"] = f"parse error: {e}"
            sitemap_meta.append(meta)
            continue
        if root.tag.lower().endswith("sitemapindex"):
            meta["type"] = "sitemapindex"
            children = [loc.text.strip() for loc in root.iter(SM_NS + "loc") if loc.text]
            meta["url_count"] = len(children)
            for c in children:
                queue.append(c)
        else:
            meta["type"] = "urlset"
            count = 0
            for url_el in root.iter(SM_NS + "url"):
                loc_el = url_el.find(SM_NS + "loc")
                if loc_el is None or not loc_el.text:
                    continue
                loc = loc_el.text.strip()
                count += 1
                entry = url_entries.setdefault(
                    loc, {"lastmod": None, "changefreq": None, "priority": None, "in_sitemaps": []})
                entry["in_sitemaps"].append(sm)
                for field in ("lastmod", "changefreq", "priority"):
                    el = url_el.find(SM_NS + field)
                    if el is not None and el.text:
                        entry[field] = el.text.strip()
            meta["url_count"] = count
        sitemap_meta.append(meta)
    return sitemap_meta, url_entries


def probe_url(loc, rules):
    status, location, body, headers = fetch_no_follow(loc)
    redirected = 300 <= status < 400
    final_url = urllib.parse.urljoin(loc, location) if (redirected and location) else loc
    x_robots = headers.get("X-Robots-Tag") if headers else None
    canonical = meta_robots = None
    if body:
        parser = PageHeadParser(loc)
        try:
            parser.feed(body)
        except Exception:
            pass
        canonical, meta_robots = parser.canonical, parser.meta_robots
    path = urllib.parse.urlparse(loc).path or "/"
    return {
        "status": status, "redirected": redirected, "final_url": final_url,
        "canonical": canonical, "meta_robots": meta_robots, "x_robots_tag": x_robots,
        "robots_disallowed": robots_disallowed(path, rules),
    }


def main():
    ap = argparse.ArgumentParser(description="Discover, parse, and probe a site's XML sitemaps.")
    ap.add_argument("source", help="Site root URL, or a sitemap URL with --sitemap")
    ap.add_argument("--sitemap", action="store_true", help="Treat source as a sitemap URL directly")
    ap.add_argument("--max-urls", type=int, default=2000, help="max listed URLs to probe (default 2000)")
    ap.add_argument("--no-probe", action="store_true", help="parse sitemaps but skip per-URL probing")
    ap.add_argument("--output", default="sitemap_inventory.json")
    args = ap.parse_args()

    if args.sitemap:
        site_root = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(args.source))
        robots = fetch_robots(site_root)
        seeds = [args.source]
    else:
        site_root = args.source.rstrip("/")
        robots = fetch_robots(site_root)
        seeds = list(robots.get("sitemaps", [])) or [
            site_root + "/sitemap.xml", site_root + "/sitemap_index.xml"]

    print(f"Sitemap seeds: {seeds}", file=sys.stderr)
    sitemap_meta, url_entries = collect_sitemaps(seeds, MAX_SITEMAPS)

    # Duplicate URLs = listed in more than one sitemap.
    duplicate_urls = sorted(loc for loc, e in url_entries.items() if len(e["in_sitemaps"]) > 1)

    urls = {}
    rules = robots.get("rules", [])
    locs = list(url_entries.keys())[: args.max_urls]
    for i, loc in enumerate(locs, 1):
        entry = dict(url_entries[loc])
        if not args.no_probe:
            entry.update(probe_url(loc, rules))
            print(f"[{entry.get('status')}] ({i}/{len(locs)}) {loc}", file=sys.stderr)
        urls[loc] = entry

    out = {
        "site": site_root,
        "robots_txt": robots,
        "sitemaps": sitemap_meta,
        "url_count": len(url_entries),
        "duplicate_urls": duplicate_urls,
        "urls": urls,
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(sitemap_meta)} sitemaps, {len(url_entries)} URLs "
          f"({len(urls)} probed) to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
