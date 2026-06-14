#!/usr/bin/env python3
"""Crawl a website (or scan local HTML files) and build a heading inventory as JSON.

Usage:
    python3 extract_headings.py https://example.com [--max-pages 500] [--output heading_inventory.json]
    python3 extract_headings.py ./site-folder --local [--output heading_inventory.json]
    python3 extract_headings.py urls.txt --url-list [--output heading_inventory.json]

Output JSON schema:
{
  "site": "https://example.com",
  "pages": {
    "<url>": {
      "status": 200,
      "title": "<title text or null>",
      "headings": [ {"level": 1, "text": "..."}, {"level": 2, "text": "..."}, ... ]
    }
  }
}

Headings are captured in document order with their level (1–6) and trimmed text.

Uses only the Python standard library.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import deque
from html.parser import HTMLParser

USER_AGENT = "HeadingAuditBot/1.0 (+claude-skill)"
TIMEOUT = 15
HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


class HeadingParser(HTMLParser):
    """Extract the page title, headings in document order, and same-host links."""

    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title = None
        self.headings = []
        self.links = []
        self._in_title = False
        self._title_parts = []
        self._heading_level = None
        self._heading_parts = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self._in_title = True
            self._title_parts = []
        elif tag in HEADING_TAGS and self._heading_level is None:
            self._heading_level = int(tag[1])
            self._heading_parts = []
        elif tag == "a" and a.get("href"):
            href = a["href"].strip()
            if not href.startswith(("mailto:", "tel:", "javascript:", "#")):
                target = urllib.parse.urljoin(self.base_url, href)
                self.links.append(urllib.parse.urldefrag(target)[0])

    def handle_endtag(self, tag):
        if tag == "title" and self._in_title:
            self._in_title = False
            self.title = " ".join("".join(self._title_parts).split()) or None
        elif tag in HEADING_TAGS and self._heading_level == int(tag[1]):
            text = " ".join("".join(self._heading_parts).split())
            self.headings.append({"level": self._heading_level, "text": text})
            self._heading_level = None

    def handle_data(self, data):
        if self._in_title:
            self._title_parts.append(data)
        if self._heading_level is not None:
            self._heading_parts.append(data)


def fetch(url):
    """Return (status, final_url, html_or_none)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            ctype = resp.headers.get("Content-Type", "")
            body = None
            if "html" in ctype or "xml" in ctype:
                body = resp.read(2_000_000).decode("utf-8", errors="replace")
            return resp.status, resp.geturl(), body
    except urllib.error.HTTPError as e:
        return e.code, url, None
    except Exception:
        return 0, url, None


def norm_host(url):
    host = urllib.parse.urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def pages_from_sitemap(site):
    status, _final, body = fetch(urllib.parse.urljoin(site, "/sitemap.xml"))
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


def parse_page(url, html):
    parser = HeadingParser(url)
    try:
        parser.feed(html)
    except Exception:
        pass
    return {"title": parser.title, "headings": parser.headings}, parser.links


def crawl(site, max_pages):
    start = site.rstrip("/")
    host = norm_host(start)
    seeds = pages_from_sitemap(start) or [start]
    queue = deque(seeds[:max_pages])
    seen = set(queue)
    pages = {}
    while queue and len(pages) < max_pages:
        url = queue.popleft()
        status, final_url, html = fetch(url)
        print(f"[{status}] {url}", file=sys.stderr)
        if html is None:
            pages[url] = {"status": status, "title": None, "headings": []}
            continue
        info, links = parse_page(final_url, html)
        info["status"] = status
        pages[url] = info
        for link in links:
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
                info, _links = parse_page("file://" + os.path.abspath(path), html)
                info["status"] = 200
                pages[os.path.relpath(path, folder)] = info
    return pages


def scan_url_list(path, max_pages):
    pages = {}
    with open(path, encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    for url in urls[:max_pages]:
        status, final_url, html = fetch(url)
        print(f"[{status}] {url}", file=sys.stderr)
        if html is None:
            pages[url] = {"status": status, "title": None, "headings": []}
            continue
        info, _links = parse_page(final_url, html)
        info["status"] = status
        pages[url] = info
    return pages


def main():
    ap = argparse.ArgumentParser(description="Build a heading inventory for a site.")
    ap.add_argument("source", help="Site root URL, local folder (--local), or URL list file (--url-list)")
    ap.add_argument("--max-pages", type=int, default=500)
    ap.add_argument("--output", default="heading_inventory.json")
    ap.add_argument("--local", action="store_true", help="Treat source as a local folder of HTML files")
    ap.add_argument("--url-list", action="store_true", help="Treat source as a text file of URLs")
    args = ap.parse_args()

    if args.local:
        pages = scan_local(args.source)
    elif args.url_list:
        pages = scan_url_list(args.source, args.max_pages)
    else:
        pages = crawl(args.source, args.max_pages)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"site": args.source, "pages": pages}, f, indent=2, ensure_ascii=False)
    total = sum(len(p.get("headings", [])) for p in pages.values())
    print(f"Wrote {len(pages)} pages ({total} headings) to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
