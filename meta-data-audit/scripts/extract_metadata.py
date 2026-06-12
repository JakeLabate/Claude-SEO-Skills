#!/usr/bin/env python3
"""Crawl a website (or scan local HTML files) and build a title/meta description inventory as JSON.

Usage:
    python3 extract_metadata.py https://example.com [--max-pages 500] [--output metadata_inventory.json]
    python3 extract_metadata.py ./site-folder --local [--output metadata_inventory.json]
    python3 extract_metadata.py urls.txt --url-list [--output metadata_inventory.json]

Output JSON schema:
{
  "site": "https://example.com",
  "pages": {
    "<url>": {
      "status": 200,
      "titles": ["..."],            # every <title> found, in order
      "descriptions": ["..."],      # every <meta name="description"> found, in order
      "h1": "<first h1 text or null>",
      "canonical": "<url or null>",
      "meta_robots": "<content or null>",
      "og_title": "<content or null>",
      "og_description": "<content or null>"
    }
  }
}

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

USER_AGENT = "MetaDataAuditBot/1.0 (+claude-skill)"
TIMEOUT = 15


class MetadataParser(HTMLParser):
    """Extract titles, meta descriptions, first H1, canonical, robots, OG tags, and links."""

    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.titles = []
        self.descriptions = []
        self.h1 = None
        self.canonical = None
        self.meta_robots = None
        self.og_title = None
        self.og_description = None
        self.links = []
        self._in_title = False
        self._title_parts = []
        self._in_h1 = False
        self._h1_parts = []
        self._h1_done = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self._in_title = True
            self._title_parts = []
        elif tag == "h1" and not self._h1_done:
            self._in_h1 = True
            self._h1_parts = []
        elif tag == "meta":
            name = (a.get("name") or "").lower()
            prop = (a.get("property") or "").lower()
            content = a.get("content")
            if name == "description":
                self.descriptions.append((content or "").strip())
            elif name == "robots":
                self.meta_robots = content
            elif prop == "og:title" and self.og_title is None:
                self.og_title = (content or "").strip() or None
            elif prop == "og:description" and self.og_description is None:
                self.og_description = (content or "").strip() or None
        elif tag == "link" and (a.get("rel") or "").lower() == "canonical" and a.get("href"):
            self.canonical = urllib.parse.urljoin(self.base_url, a["href"])
        elif tag == "a" and a.get("href"):
            href = a["href"].strip()
            if not href.startswith(("mailto:", "tel:", "javascript:", "#")):
                target = urllib.parse.urljoin(self.base_url, href)
                self.links.append(urllib.parse.urldefrag(target)[0])

    def handle_endtag(self, tag):
        if tag == "title" and self._in_title:
            self._in_title = False
            self.titles.append(" ".join("".join(self._title_parts).split()))
        elif tag == "h1" and self._in_h1:
            self._in_h1 = False
            self._h1_done = True
            self.h1 = " ".join("".join(self._h1_parts).split()) or None

    def handle_data(self, data):
        if self._in_title:
            self._title_parts.append(data)
        if self._in_h1:
            self._h1_parts.append(data)


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
        return 0, url, None  # 0 = network/connection error


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
    parser = MetadataParser(url)
    try:
        parser.feed(html)
    except Exception:
        pass
    info = {
        "titles": parser.titles,
        "descriptions": parser.descriptions,
        "h1": parser.h1,
        "canonical": parser.canonical,
        "meta_robots": parser.meta_robots,
        "og_title": parser.og_title,
        "og_description": parser.og_description,
    }
    return info, parser.links


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
            pages[url] = {"status": status, "titles": [], "descriptions": [], "h1": None,
                          "canonical": None, "meta_robots": None,
                          "og_title": None, "og_description": None}
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
            pages[url] = {"status": status, "titles": [], "descriptions": [], "h1": None,
                          "canonical": None, "meta_robots": None,
                          "og_title": None, "og_description": None}
            continue
        info, _links = parse_page(final_url, html)
        info["status"] = status
        pages[url] = info
    return pages


def main():
    ap = argparse.ArgumentParser(description="Build a title/meta description inventory for a site.")
    ap.add_argument("source", help="Site root URL, local folder (--local), or URL list file (--url-list)")
    ap.add_argument("--max-pages", type=int, default=500)
    ap.add_argument("--output", default="metadata_inventory.json")
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
    titles = sum(len(p["titles"]) for p in pages.values())
    descs = sum(len(p["descriptions"]) for p in pages.values())
    print(f"Wrote {len(pages)} pages ({titles} titles, {descs} descriptions) to {args.output}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
