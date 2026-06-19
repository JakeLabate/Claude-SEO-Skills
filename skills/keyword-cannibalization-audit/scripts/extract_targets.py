#!/usr/bin/env python3
"""Crawl a site and capture each page's keyword-target signals.

Usage:
    python3 extract_targets.py https://example.com [--max-pages 500] [--output target_inventory.json]
    python3 extract_targets.py urls.txt --url-list [--output target_inventory.json]

For each page it records status, title, first H1, meta description, noindex, and
the page's top body keywords by frequency (stopword-filtered). The auditor uses
the title + H1 + top keywords to find multiple pages targeting the same query
(keyword cannibalization).

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
from collections import Counter, deque
from html.parser import HTMLParser

USER_AGENT = "CannibalizationAuditBot/1.0 (+claude-skill)"
TIMEOUT = 15
TOP_KEYWORDS = 15
SKIP_TEXT_TAGS = {"script", "style", "noscript", "template", "svg"}

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "has", "have", "how", "in", "is", "it", "its", "of", "on", "or", "our",
    "that", "the", "this", "to", "was", "we", "what", "when", "where", "which",
    "who", "will", "with", "you", "your", "can", "do", "does", "get", "more",
    "all", "about", "into", "than", "then", "they", "their", "if", "so", "no",
}


class TargetParser(HTMLParser):
    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title = None
        self.h1 = None
        self.description = None
        self.meta_robots = None
        self.tokens = []
        self.links = []
        self._in_title = False
        self._title = []
        self._in_h1 = False
        self._h1 = []
        self._h1_done = False
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in SKIP_TEXT_TAGS:
            self._skip += 1
        if tag == "title":
            self._in_title, self._title = True, []
        elif tag == "h1" and not self._h1_done:
            self._in_h1, self._h1 = True, []
        elif tag == "meta":
            name = (a.get("name") or "").lower()
            if name == "description":
                self.description = (a.get("content") or "").strip() or None
            elif name == "robots":
                self.meta_robots = a.get("content")
        elif tag == "a" and a.get("href"):
            href = a["href"].strip()
            if not href.startswith(("mailto:", "tel:", "javascript:", "#")):
                self.links.append(
                    urllib.parse.urldefrag(urllib.parse.urljoin(self.base_url, href))[0])

    def handle_endtag(self, tag):
        if tag in SKIP_TEXT_TAGS and self._skip > 0:
            self._skip -= 1
        if tag == "title":
            self._in_title = False
            self.title = " ".join("".join(self._title).split()) or None
        elif tag == "h1" and self._in_h1:
            self._in_h1, self._h1_done = False, True
            self.h1 = " ".join("".join(self._h1).split()) or None

    def handle_data(self, data):
        if self._in_title:
            self._title.append(data)
        if self._in_h1:
            self._h1.append(data)
        if self._skip == 0:
            self.tokens.extend(
                w for w in re.findall(r"[a-z][a-z0-9']+", data.lower())
                if w not in STOPWORDS and len(w) > 2)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            ctype = resp.headers.get("Content-Type", "")
            body = resp.read(2_000_000).decode("utf-8", errors="replace") \
                if "html" in ctype else None
            return resp.status, resp.geturl(), body
    except urllib.error.HTTPError as e:
        return e.code, url, None
    except Exception:
        return 0, url, None


def norm_host(url):
    h = urllib.parse.urlparse(url).netloc.lower()
    return h[4:] if h.startswith("www.") else h


def pages_from_sitemap(site):
    status, _f, body = fetch(urllib.parse.urljoin(site, "/sitemap.xml"))
    if status != 200 or not body:
        return []
    try:
        root = ET.fromstring(body)
        return [loc.text.strip() for loc in
                root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc") if loc.text]
    except ET.ParseError:
        return []


def analyze(url, html):
    p = TargetParser(url)
    try:
        p.feed(html)
    except Exception:
        pass
    top = [w for w, _c in Counter(p.tokens).most_common(TOP_KEYWORDS)]
    info = {"title": p.title, "h1": p.h1, "description": p.description,
            "noindex": "noindex" in (p.meta_robots or "").lower(),
            "word_count": len(p.tokens), "top_keywords": top}
    return info, p.links


def extract_from_cache(cache_path):
    """Pure: turn a shared page cache (from fetch_pages.py) into a target inventory.

    No network — analyzes the cached HTML for exactly the signals this audit needs.
    """
    with open(cache_path, encoding="utf-8") as f:
        cache = json.load(f)
    pages = {}
    for url, page in cache.get("pages", {}).items():
        html = page.get("html")
        status = page.get("status", 0)
        final_url = page.get("final_url") or url
        if not html:
            pages[url] = {"status": status, "final_url": final_url, "title": None,
                          "h1": None, "description": None, "noindex": False,
                          "word_count": 0, "top_keywords": []}
            continue
        info, _links = analyze(final_url, html)
        info["status"] = status
        info["final_url"] = final_url
        pages[url] = info
    return cache.get("site", cache_path), pages


def collect(urls, max_pages, crawl_host=None):
    pages, queue, seen = {}, deque(urls), set(urls)
    while queue and len(pages) < max_pages:
        url = queue.popleft()
        status, final_url, html = fetch(url)
        print(f"[{status}] {url}", file=sys.stderr)
        if html is None:
            pages[url] = {"status": status, "final_url": final_url, "title": None,
                          "h1": None, "description": None, "noindex": False,
                          "word_count": 0, "top_keywords": []}
            continue
        info, links = analyze(final_url, html)
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
    ap = argparse.ArgumentParser(description="Capture keyword-target signals for a site.")
    ap.add_argument("source", nargs="?")
    ap.add_argument("--from-cache",
                    help="Extract from a shared page cache produced by fetch_pages.py (no network)")
    ap.add_argument("--max-pages", type=int, default=500)
    ap.add_argument("--output", default="target_inventory.json")
    ap.add_argument("--url-list", action="store_true")
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

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"site": site, "pages": pages}, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(pages)} pages to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
