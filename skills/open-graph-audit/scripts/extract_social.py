#!/usr/bin/env python3
"""Crawl a site and build an Open Graph / Twitter Card inventory, probing og:image.

Usage:
    python3 extract_social.py https://example.com [--max-pages 500] [--output social_inventory.json]
    python3 extract_social.py urls.txt --url-list [--output social_inventory.json]

Records per page: status, final_url, canonical, meta robots, and all OG and
Twitter Card tags (title, description, image, url, type, card). Each unique
og:image / twitter:image is probed once for HTTP status and content type so the
auditor can flag broken or non-image share images.

Uses only the Python standard library.
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import deque
from html.parser import HTMLParser

USER_AGENT = "OpenGraphAuditBot/1.0 (+claude-skill)"
TIMEOUT = 15

OG_KEYS = {"og:title", "og:description", "og:image", "og:image:secure_url",
           "og:url", "og:type", "og:site_name", "og:image:width", "og:image:height"}
TW_KEYS = {"twitter:card", "twitter:title", "twitter:description", "twitter:image",
           "twitter:site"}


class SocialParser(HTMLParser):
    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.og = {}
        self.tw = {}
        self.canonical = None
        self.meta_robots = None
        self.links = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            prop = (a.get("property") or "").lower()
            name = (a.get("name") or "").lower()
            content = (a.get("content") or "").strip()
            if prop in OG_KEYS and prop not in self.og:
                self.og[prop] = content
            elif name in TW_KEYS and name not in self.tw:
                self.tw[name] = content
            elif name == "robots":
                self.meta_robots = a.get("content")
        elif tag == "link" and (a.get("rel") or "").lower() == "canonical" and a.get("href"):
            self.canonical = urllib.parse.urljoin(self.base_url, a["href"])
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
            body = None
            if "html" in ctype or "xml" in ctype:
                body = resp.read(2_000_000).decode("utf-8", errors="replace")
            return resp.status, resp.geturl(), body, ctype
    except urllib.error.HTTPError as e:
        return e.code, url, None, ""
    except Exception:
        return 0, url, None, ""


def norm_host(url):
    h = urllib.parse.urlparse(url).netloc.lower()
    return h[4:] if h.startswith("www.") else h


def pages_from_sitemap(site):
    status, _f, body, _c = fetch(urllib.parse.urljoin(site, "/sitemap.xml"))
    if status != 200 or not body:
        return []
    try:
        root = ET.fromstring(body)
        return [loc.text.strip() for loc in
                root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc") if loc.text]
    except ET.ParseError:
        return []


def parse_page(url, html):
    p = SocialParser(url)
    try:
        p.feed(html)
    except Exception:
        pass
    return {"og": p.og, "twitter": p.tw, "canonical": p.canonical,
            "meta_robots": p.meta_robots}, p.links


def empty(status, final_url):
    return {"status": status, "final_url": final_url, "og": {}, "twitter": {},
            "canonical": None, "meta_robots": None}


def extract_from_cache(cache_path):
    """Pure: turn a shared page cache (from fetch_pages.py) into a social inventory.

    No network — parses the cached HTML for exactly the fields this audit needs.
    (The optional share-image probe still hits the network unless --no-probe.)
    """
    with open(cache_path, encoding="utf-8") as f:
        cache = json.load(f)
    pages = {}
    for url, page in cache.get("pages", {}).items():
        html = page.get("html")
        status = page.get("status", 0)
        final_url = page.get("final_url") or url
        if not html:
            pages[url] = empty(status, final_url)
            continue
        info, _links = parse_page(final_url, html)
        info["status"] = status
        info["final_url"] = final_url
        pages[url] = info
    return cache.get("site", cache_path), pages


def collect(urls, max_pages, crawl_host=None):
    pages, queue, seen = {}, deque(urls), set(urls)
    while queue and len(pages) < max_pages:
        url = queue.popleft()
        status, final_url, html, _c = fetch(url)
        print(f"[{status}] {url}", file=sys.stderr)
        if html is None:
            pages[url] = empty(status, final_url)
            continue
        info, links = parse_page(final_url, html)
        info["status"] = status
        info["final_url"] = final_url
        pages[url] = info
        if crawl_host:
            for link in links:
                if norm_host(link) == crawl_host and link not in seen:
                    seen.add(link)
                    queue.append(link)
    return pages


def probe_images(pages):
    wanted = set()
    for p in pages.values():
        for key in ("og:image", "og:image:secure_url"):
            if p.get("og", {}).get(key):
                wanted.add(p["og"][key])
        if p.get("twitter", {}).get("twitter:image"):
            wanted.add(p["twitter"]["twitter:image"])
    images = {}
    for url in sorted(wanted):
        if not urllib.parse.urlparse(url).scheme:
            images[url] = {"status": 0, "content_type": "", "absolute": False}
            continue
        status, _f, _b, ctype = fetch(url)
        print(f"  og:image [{status}] {url}", file=sys.stderr)
        images[url] = {"status": status, "content_type": ctype, "absolute": True}
    return images


def main():
    ap = argparse.ArgumentParser(description="Build an Open Graph / Twitter Card inventory.")
    ap.add_argument("source", nargs="?")
    ap.add_argument("--from-cache",
                    help="Extract from a shared page cache produced by fetch_pages.py (no network)")
    ap.add_argument("--max-pages", type=int, default=500)
    ap.add_argument("--output", default="social_inventory.json")
    ap.add_argument("--url-list", action="store_true")
    ap.add_argument("--no-probe", action="store_true", help="skip probing share images")
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

    images = {} if args.no_probe else probe_images(pages)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"site": site, "pages": pages, "images": images},
                  f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(pages)} pages, {len(images)} share images to {args.output}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
