#!/usr/bin/env python3
"""Crawl a site and build a canonical-tag inventory, probing each canonical target.

Usage:
    python3 extract_canonicals.py https://example.com [--max-pages 500] [--output canonical_inventory.json]
    python3 extract_canonicals.py urls.txt --url-list [--output canonical_inventory.json]

For every crawled page it records the page status, every <link rel="canonical">
found (raw href + resolved absolute URL), the HTTP `Link: rel=canonical` header,
meta robots, and the `X-Robots-Tag` header. It then probes each unique canonical
target once for status, redirect, and noindex so the auditor can tell whether a
canonical points at a final, indexable 200 URL.

Output JSON schema:
{
  "site": "...",
  "pages": { "<url>": {
      "status": 200, "final_url": "...",
      "canonicals": [{"raw": "...", "resolved": "..."}],
      "header_canonical": "<url or null>",
      "meta_robots": "<content or null>",
      "x_robots": "<header or null>"
  }},
  "targets": { "<canonical_url>": {
      "status": 200, "redirects_to": "<url or null>", "noindex": false
  }}
}

Uses only the Python standard library.
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import deque
from html.parser import HTMLParser

USER_AGENT = "CanonicalAuditBot/1.0 (+claude-skill)"
TIMEOUT = 15

LINK_HEADER_RE = re.compile(r'<([^>]+)>\s*;\s*rel\s*=\s*"?canonical"?', re.I)


class HeadParser(HTMLParser):
    """Extract canonical link tags, meta robots, and same-host anchor links."""

    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.canonicals = []
        self.meta_robots = None
        self.links = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "link" and (a.get("rel") or "").lower() == "canonical":
            raw = (a.get("href") or "").strip()
            if raw:
                self.canonicals.append(
                    {"raw": raw, "resolved": urllib.parse.urljoin(self.base_url, raw)})
        elif tag == "meta" and (a.get("name") or "").lower() == "robots":
            self.meta_robots = a.get("content")
        elif tag == "a" and a.get("href"):
            href = a["href"].strip()
            if not href.startswith(("mailto:", "tel:", "javascript:", "#")):
                target = urllib.parse.urljoin(self.base_url, href)
                self.links.append(urllib.parse.urldefrag(target)[0])


def fetch(url):
    """Return (status, final_url, body, headers)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            ctype = resp.headers.get("Content-Type", "")
            body = None
            if "html" in ctype or "xml" in ctype:
                body = resp.read(2_000_000).decode("utf-8", errors="replace")
            return resp.status, resp.geturl(), body, dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, url, None, dict(e.headers or {})
    except Exception:
        return 0, url, None, {}


def head_or_get(url):
    """Probe a canonical target: return (status, redirects_to, noindex)."""
    status, final_url, body, headers = fetch(url)
    redirects_to = final_url if final_url and final_url != url else None
    x_robots = headers.get("X-Robots-Tag", "") or ""
    noindex = "noindex" in x_robots.lower()
    if body and not noindex:
        m = re.search(r'<meta[^>]+name=["\']robots["\'][^>]*>', body, re.I)
        if m and "noindex" in m.group(0).lower():
            noindex = True
    return status, redirects_to, noindex


def norm_host(url):
    host = urllib.parse.urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def pages_from_sitemap(site):
    status, _f, body, _h = fetch(urllib.parse.urljoin(site, "/sitemap.xml"))
    if status != 200 or not body:
        return []
    urls = []
    try:
        root = ET.fromstring(body)
        for loc in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
            if loc.text:
                urls.append(loc.text.strip())
    except ET.ParseError:
        return []
    return urls


def parse_page(url, html, headers):
    parser = HeadParser(url)
    try:
        parser.feed(html)
    except Exception:
        pass
    header_canonical = None
    link_header = headers.get("Link", "")
    m = LINK_HEADER_RE.search(link_header or "")
    if m:
        header_canonical = urllib.parse.urljoin(url, m.group(1).strip())
    info = {
        "canonicals": parser.canonicals,
        "header_canonical": header_canonical,
        "meta_robots": parser.meta_robots,
        "x_robots": headers.get("X-Robots-Tag"),
    }
    return info, parser.links


def empty_page(status, final_url):
    return {"status": status, "final_url": final_url, "canonicals": [],
            "header_canonical": None, "meta_robots": None, "x_robots": None}


def extract_from_cache(cache_path):
    """Pure: turn a shared page cache (from fetch_pages.py) into a canonical inventory.

    Reads the cached HTML *and response headers* (the Link: rel=canonical and
    X-Robots-Tag headers this audit needs). The canonical-target probe is left to
    the caller — those targets may sit outside the crawl set.
    """
    with open(cache_path, encoding="utf-8") as f:
        cache = json.load(f)
    pages = {}
    for url, page in cache.get("pages", {}).items():
        html = page.get("html")
        status = page.get("status", 0)
        final_url = page.get("final_url") or url
        if not html:
            pages[url] = empty_page(status, final_url)
            continue
        info, _links = parse_page(final_url, html, page.get("headers") or {})
        info["status"] = status
        info["final_url"] = final_url
        pages[url] = info
    return cache.get("site", cache_path), pages


def collect(urls_iter, max_pages, crawl_host=None):
    pages = {}
    queue = deque(urls_iter)
    seen = set(queue)
    while queue and len(pages) < max_pages:
        url = queue.popleft()
        status, final_url, html, headers = fetch(url)
        print(f"[{status}] {url}", file=sys.stderr)
        if html is None:
            pages[url] = empty_page(status, final_url)
            continue
        info, links = parse_page(final_url, html, headers)
        info["status"] = status
        info["final_url"] = final_url
        pages[url] = info
        if crawl_host:
            for link in links:
                if norm_host(link) == crawl_host and link not in seen:
                    seen.add(link)
                    queue.append(link)
    return pages


def probe_targets(pages):
    wanted = set()
    for page in pages.values():
        for c in page.get("canonicals", []):
            wanted.add(c["resolved"])
        if page.get("header_canonical"):
            wanted.add(page["header_canonical"])
    targets = {}
    for url in sorted(wanted):
        status, redirects_to, noindex = head_or_get(url)
        print(f"  canonical target [{status}] {url}", file=sys.stderr)
        targets[url] = {"status": status, "redirects_to": redirects_to, "noindex": noindex}
    return targets


def main():
    ap = argparse.ArgumentParser(description="Build a canonical-tag inventory for a site.")
    ap.add_argument("source", nargs="?", help="Site root URL, or URL list file with --url-list")
    ap.add_argument("--from-cache",
                    help="Extract from a shared page cache produced by fetch_pages.py (no crawl)")
    ap.add_argument("--max-pages", type=int, default=500)
    ap.add_argument("--output", default="canonical_inventory.json")
    ap.add_argument("--url-list", action="store_true")
    ap.add_argument("--no-probe", action="store_true", help="skip probing canonical targets")
    args = ap.parse_args()

    if args.from_cache:
        site, pages = extract_from_cache(args.from_cache)
    elif not args.source:
        ap.error("provide a source, or --from-cache page_cache.json")
    elif args.url_list:
        with open(args.source, encoding="utf-8") as f:
            urls = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        site, pages = args.source, collect(urls[: args.max_pages], args.max_pages)
    else:
        start = args.source.rstrip("/")
        seeds = pages_from_sitemap(start) or [start]
        site, pages = args.source, collect(seeds[: args.max_pages], args.max_pages,
                                           crawl_host=norm_host(start))

    targets = {} if args.no_probe else probe_targets(pages)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"site": site, "pages": pages, "targets": targets},
                  f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(pages)} pages, {len(targets)} canonical targets to {args.output}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
