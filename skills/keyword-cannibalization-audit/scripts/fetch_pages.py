#!/usr/bin/env python3
"""Crawl a website once and write a raw page cache that every audit can extract from.

This is the *fetch* stage of the pipeline, split out from per-skill collectors so a
site is crawled a single time and all audits read from the same snapshot:

    fetch (this script)  ->  page_cache.json  ->  extract_*.py (pure)  ->  *_inventory.json

The cache stores raw HTML and the response facts every collector needs, and nothing
audit-specific — each skill's extractor pulls only the bits it cares about. Because
fetching is the only network stage, everything downstream is pure and re-runnable
offline.

Usage:
    python3 fetch_pages.py https://example.com [--max-pages 500] [--output page_cache.json]
    python3 fetch_pages.py ./site-folder --local  [--output page_cache.json]
    python3 fetch_pages.py urls.txt --url-list     [--output page_cache.json]

Output JSON schema:
{
  "site": "https://example.com",
  "mode": "crawl" | "local" | "url-list",
  "fetched_at": "2026-06-19T12:00:00Z",
  "pages": {
    "<requested url or local relpath>": {
      "status": 200,                # HTTP status; 0 = network/connection error
      "final_url": "<url after redirects>",
      "content_type": "text/html; charset=utf-8",
      "headers": {"Link": "...", "X-Robots-Tag": "..."},  # response headers
      "html": "<!doctype html>..."  # null for non-HTML or failed fetches
    }
  }
}

Uses only the Python standard library.
"""

import argparse
import datetime
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import deque
from html.parser import HTMLParser

USER_AGENT = "SEOAuditBot/1.0 (+claude-skill)"
TIMEOUT = 15
MAX_BYTES = 2_000_000


class LinkParser(HTMLParser):
    """Pull same-document <a href> links so the crawler can do a same-host BFS.

    The fetch stage only needs links to know where to crawl next — every other
    tag is left for the per-skill extractors to parse from the cached HTML.
    """

    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        a = dict(attrs)
        href = (a.get("href") or "").strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
            return
        target = urllib.parse.urljoin(self.base_url, href)
        self.links.append(urllib.parse.urldefrag(target)[0])


def fetch(url):
    """Return (status, final_url, content_type, headers, html_or_none)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            ctype = resp.headers.get("Content-Type", "")
            body = None
            if "html" in ctype or "xml" in ctype:
                body = resp.read(MAX_BYTES).decode("utf-8", errors="replace")
            return resp.status, resp.geturl(), ctype, dict(resp.headers), body
    except urllib.error.HTTPError as e:
        hdrs = dict(e.headers or {})
        return e.code, url, hdrs.get("Content-Type", ""), hdrs, None
    except Exception:
        return 0, url, "", {}, None  # 0 = network/connection error


def norm_host(url):
    host = urllib.parse.urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def links_in(final_url, html):
    parser = LinkParser(final_url)
    try:
        parser.feed(html)
    except Exception:
        pass
    return parser.links


def pages_from_sitemap(site):
    _status, _final, _ctype, _headers, body = fetch(urllib.parse.urljoin(site, "/sitemap.xml"))
    if not body:
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


def record(status, final_url, content_type, headers, html):
    return {"status": status, "final_url": final_url,
            "content_type": content_type, "headers": headers, "html": html}


def crawl(site, max_pages):
    start = site.rstrip("/")
    host = norm_host(start)
    seeds = pages_from_sitemap(start) or [start]
    queue = deque(seeds[:max_pages])
    seen = set(queue)
    pages = {}
    while queue and len(pages) < max_pages:
        url = queue.popleft()
        status, final_url, ctype, headers, html = fetch(url)
        print(f"[{status}] {url}", file=sys.stderr)
        pages[url] = record(status, final_url, ctype, headers, html)
        if not html:
            continue
        for link in links_in(final_url, html):
            if norm_host(link) == host and link not in seen:
                seen.add(link)
                queue.append(link)
    return pages


def scan_local(folder):
    pages = {}
    for root, _dirs, files in os.walk(folder):
        for name in files:
            if name.lower().endswith((".html", ".htm")):
                path = os.path.join(root, name)
                with open(path, encoding="utf-8", errors="replace") as f:
                    html = f.read()
                rel = os.path.relpath(path, folder)
                pages[rel] = record(200, "file://" + os.path.abspath(path),
                                    "text/html", {}, html)
    return pages


def scan_url_list(path, max_pages):
    pages = {}
    with open(path, encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    for url in urls[:max_pages]:
        status, final_url, ctype, headers, html = fetch(url)
        print(f"[{status}] {url}", file=sys.stderr)
        pages[url] = record(status, final_url, ctype, headers, html)
    return pages


def main():
    ap = argparse.ArgumentParser(description="Crawl once into a raw page cache for SEO audits.")
    ap.add_argument("source", help="Site root URL, local folder (--local), or URL list file (--url-list)")
    ap.add_argument("--max-pages", type=int, default=500)
    ap.add_argument("--output", default="page_cache.json")
    ap.add_argument("--local", action="store_true", help="Treat source as a local folder of HTML files")
    ap.add_argument("--url-list", action="store_true", help="Treat source as a text file of URLs")
    args = ap.parse_args()

    if args.local:
        mode, pages = "local", scan_local(args.source)
    elif args.url_list:
        mode, pages = "url-list", scan_url_list(args.source, args.max_pages)
    else:
        mode, pages = "crawl", crawl(args.source, args.max_pages)

    cache = {
        "site": args.source,
        "mode": mode,
        "fetched_at": datetime.datetime.now(datetime.timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pages": pages,
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)
    html_pages = sum(1 for p in pages.values() if p["html"])
    print(f"Cached {len(pages)} pages ({html_pages} with HTML) to {args.output}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
