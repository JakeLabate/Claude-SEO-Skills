#!/usr/bin/env python3
"""Crawl a site and inventory pagination signals (rel=next/prev, canonical, page params).

Usage:
    python3 extract_pagination.py https://example.com [--max-pages 500] [--output pagination_inventory.json]
    python3 extract_pagination.py urls.txt --url-list [--output pagination_inventory.json]

For each page it records status, final_url, canonical, meta robots, the
`rel="next"` / `rel="prev"` link targets (from <link> tags and the HTTP Link
header), and the detected page number from the URL (?page=N, /page/N, etc.).

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

USER_AGENT = "PaginationAuditBot/1.0 (+claude-skill)"
TIMEOUT = 15

LINK_HEADER_RE = re.compile(r'<([^>]+)>\s*;\s*rel\s*=\s*"?(next|prev)"?', re.I)
# Page-number patterns: ?page=2, &p=2, /page/2, /page/2/, .../2 in a paged path.
PAGE_PATTERNS = [
    re.compile(r'[?&](?:page|p|pg|paged)=(\d+)', re.I),
    re.compile(r'/page/(\d+)/?', re.I),
    re.compile(r'/p/(\d+)/?', re.I),
]


def page_number(url):
    """Return the page number encoded in the URL, or None if it isn't paginated."""
    for pat in PAGE_PATTERNS:
        m = pat.search(url)
        if m:
            return int(m.group(1))
    return None


class PaginationParser(HTMLParser):
    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.rel_next = None
        self.rel_prev = None
        self.canonical = None
        self.meta_robots = None
        self.links = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "link":
            rel = (a.get("rel") or "").lower()
            href = a.get("href")
            if href:
                resolved = urllib.parse.urljoin(self.base_url, href.strip())
                if "next" in rel:
                    self.rel_next = resolved
                elif "prev" in rel:
                    self.rel_prev = resolved
                elif rel == "canonical":
                    self.canonical = resolved
        elif tag == "meta" and (a.get("name") or "").lower() == "robots":
            self.meta_robots = a.get("content")
        elif tag == "a" and a.get("href"):
            href = a["href"].strip()
            if not href.startswith(("mailto:", "tel:", "javascript:", "#")):
                self.links.append(
                    urllib.parse.urldefrag(urllib.parse.urljoin(self.base_url, href))[0])


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            ctype = resp.headers.get("Content-Type", "")
            body = resp.read(2_000_000).decode("utf-8", errors="replace") \
                if ("html" in ctype or "xml" in ctype) else None
            return resp.status, resp.geturl(), body, dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, url, None, dict(e.headers or {})
    except Exception:
        return 0, url, None, {}


def norm_host(url):
    h = urllib.parse.urlparse(url).netloc.lower()
    return h[4:] if h.startswith("www.") else h


def pages_from_sitemap(site):
    status, _f, body, _h = fetch(urllib.parse.urljoin(site, "/sitemap.xml"))
    if status != 200 or not body:
        return []
    try:
        root = ET.fromstring(body)
        return [loc.text.strip() for loc in
                root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc") if loc.text]
    except ET.ParseError:
        return []


def parse_page(url, html, headers):
    p = PaginationParser(url)
    try:
        p.feed(html)
    except Exception:
        pass
    for href, rel in LINK_HEADER_RE.findall(headers.get("Link", "") or ""):
        resolved = urllib.parse.urljoin(url, href.strip())
        if rel.lower() == "next" and not p.rel_next:
            p.rel_next = resolved
        elif rel.lower() == "prev" and not p.rel_prev:
            p.rel_prev = resolved
    return {"canonical": p.canonical, "meta_robots": p.meta_robots,
            "rel_next": p.rel_next, "rel_prev": p.rel_prev,
            "page_number": page_number(url)}, p.links


def collect(urls, max_pages, crawl_host=None):
    pages, queue, seen = {}, deque(urls), set(urls)
    while queue and len(pages) < max_pages:
        url = queue.popleft()
        status, final_url, html, headers = fetch(url)
        print(f"[{status}] {url}", file=sys.stderr)
        if html is None:
            pages[url] = {"status": status, "final_url": final_url, "canonical": None,
                          "meta_robots": None, "rel_next": None, "rel_prev": None,
                          "page_number": page_number(url)}
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


def main():
    ap = argparse.ArgumentParser(description="Build a pagination inventory for a site.")
    ap.add_argument("source")
    ap.add_argument("--max-pages", type=int, default=500)
    ap.add_argument("--output", default="pagination_inventory.json")
    ap.add_argument("--url-list", action="store_true")
    args = ap.parse_args()

    if args.url_list:
        with open(args.source, encoding="utf-8") as f:
            urls = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        pages = collect(urls[: args.max_pages], args.max_pages)
    else:
        start = args.source.rstrip("/")
        seeds = pages_from_sitemap(start) or [start]
        pages = collect(seeds[: args.max_pages], args.max_pages, crawl_host=norm_host(start))

    paginated = sum(1 for p in pages.values()
                    if p.get("page_number") or p.get("rel_next") or p.get("rel_prev"))
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"site": args.source, "pages": pages}, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(pages)} pages ({paginated} pagination-related) to {args.output}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
