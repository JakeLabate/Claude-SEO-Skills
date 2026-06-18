#!/usr/bin/env python3
"""Crawl a website (or scan local HTML files) and build an image inventory as JSON.

Usage:
    python3 extract_images.py https://example.com [--max-pages 500] [--check-files]
        [--output image_inventory.json]
    python3 extract_images.py ./site-folder --local [--output image_inventory.json]
    python3 extract_images.py urls.txt --url-list [--output image_inventory.json]

With --check-files the script also issues a lightweight request per unique image URL
to record HTTP status, content type, and byte size (needed for the broken-image,
oversized-file, and format checks).

Output JSON schema:
{
  "site": "https://example.com",
  "checked_files": true,
  "pages": {
    "<url>": {
      "status": 200,
      "images": [
        {
          "src": "<absolute url or null>",
          "alt": "<string, or null if the attribute is absent>",
          "width": "<attr value or null>",
          "height": "<attr value or null>",
          "loading": "<attr value or null>",
          "has_srcset": false,
          "in_picture": false,
          "position": 0            # 0-based order within the page
        }
      ]
    }
  },
  "files": {                       # only present with --check-files
    "<image url>": {"status": 200, "content_type": "image/webp", "bytes": 12345}
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

USER_AGENT = "ImageSeoAuditBot/1.0 (+claude-skill)"
TIMEOUT = 15


class ImageParser(HTMLParser):
    """Extract <img> elements (with attributes), <picture> context, and same-host links."""

    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.images = []
        self.links = []
        self._picture_depth = 0
        self._position = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "picture":
            self._picture_depth += 1
        elif tag == "img":
            src = a.get("src") or a.get("data-src")
            self.images.append({
                "src": urllib.parse.urljoin(self.base_url, src.strip()) if src else None,
                "alt": a["alt"] if "alt" in a else None,
                "width": a.get("width"),
                "height": a.get("height"),
                "loading": (a.get("loading") or "").lower() or None,
                "has_srcset": bool(a.get("srcset") or a.get("data-srcset")),
                "in_picture": self._picture_depth > 0,
                "position": self._position,
            })
            self._position += 1
        elif tag == "a" and a.get("href"):
            href = a["href"].strip()
            if not href.startswith(("mailto:", "tel:", "javascript:", "#")):
                target = urllib.parse.urljoin(self.base_url, href)
                self.links.append(urllib.parse.urldefrag(target)[0])

    def handle_endtag(self, tag):
        if tag == "picture" and self._picture_depth > 0:
            self._picture_depth -= 1


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


def head(url):
    """Return (status, content_type, byte_size) for an image URL using a HEAD request."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            length = resp.headers.get("Content-Length")
            return resp.status, resp.headers.get("Content-Type", "") or "", int(length) if length else None
    except urllib.error.HTTPError as e:
        return e.code, "", None
    except Exception:
        return 0, "", None


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
    parser = ImageParser(url)
    try:
        parser.feed(html)
    except Exception:
        pass
    return {"images": parser.images}, parser.links


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
            pages[url] = {"status": status, "images": []}
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
            pages[url] = {"status": status, "images": []}
            continue
        info, _links = parse_page(final_url, html)
        info["status"] = status
        pages[url] = info
    return pages


def check_files(pages):
    files = {}
    unique = set()
    for page in pages.values():
        for img in page.get("images", []):
            if img.get("src") and img["src"].startswith(("http://", "https://")):
                unique.add(img["src"])
    for i, src in enumerate(sorted(unique), 1):
        status, ctype, size = head(src)
        files[src] = {"status": status, "content_type": ctype, "bytes": size}
        print(f"  file {i}/{len(unique)} [{status}] {src}", file=sys.stderr)
    return files


def main():
    ap = argparse.ArgumentParser(description="Build an image inventory for a site.")
    ap.add_argument("source", help="Site root URL, local folder (--local), or URL list file (--url-list)")
    ap.add_argument("--max-pages", type=int, default=500)
    ap.add_argument("--output", default="image_inventory.json")
    ap.add_argument("--local", action="store_true", help="Treat source as a local folder of HTML files")
    ap.add_argument("--url-list", action="store_true", help="Treat source as a text file of URLs")
    ap.add_argument("--check-files", action="store_true",
                    help="HEAD-request each image URL to record status, type, and byte size")
    args = ap.parse_args()

    if args.local:
        pages = scan_local(args.source)
    elif args.url_list:
        pages = scan_url_list(args.source, args.max_pages)
    else:
        pages = crawl(args.source, args.max_pages)

    out = {"site": args.source, "checked_files": bool(args.check_files), "pages": pages}
    if args.check_files:
        out["files"] = check_files(pages)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    total_imgs = sum(len(p.get("images", [])) for p in pages.values())
    print(f"Wrote {len(pages)} pages ({total_imgs} images) to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
