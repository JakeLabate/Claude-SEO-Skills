#!/usr/bin/env python3
"""Crawl a site and capture per-page signals used to detect soft 404s.

Usage:
    python3 extract_pages.py https://example.com [--max-pages 500] [--output soft404_inventory.json]
    python3 extract_pages.py urls.txt --url-list [--output soft404_inventory.json]

A "soft 404" is a page that returns HTTP 200 but is really a "not found" / empty /
error page. For each page this records status, final_url, title, first H1, visible
word count, and whether known error phrases appear in the title/H1/body. It also
sends one request to a deliberately non-existent URL to learn how the site handles
missing pages (a proper 404, or a 200 "soft" page).

Uses only the Python standard library.
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from collections import deque
from html.parser import HTMLParser

USER_AGENT = "Soft404AuditBot/1.0 (+claude-skill)"
TIMEOUT = 15

ERROR_PHRASES = [
    "404", "not found", "page not found", "page doesn't exist",
    "page does not exist", "cannot be found", "can't be found",
    "no longer available", "no longer exists", "nothing found",
    "page you requested", "page you were looking for", "oops",
    "sorry, we couldn", "this page isn", "doesn't exist",
]
SKIP_TEXT_TAGS = {"script", "style", "noscript", "template", "svg"}


class PageParser(HTMLParser):
    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title = None
        self.h1 = None
        self.text_words = 0
        self.links = []
        self._in_title = False
        self._title = []
        self._in_h1 = False
        self._h1 = []
        self._h1_done = False
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in SKIP_TEXT_TAGS:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
            self._title = []
        elif tag == "h1" and not self._h1_done:
            self._in_h1 = True
            self._h1 = []
        elif tag == "a" and a.get("href"):
            href = a["href"].strip()
            if not href.startswith(("mailto:", "tel:", "javascript:", "#")):
                self.links.append(
                    urllib.parse.urldefrag(urllib.parse.urljoin(self.base_url, href))[0])

    def handle_endtag(self, tag):
        if tag in SKIP_TEXT_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False
            self.title = " ".join("".join(self._title).split()) or None
        elif tag == "h1" and self._in_h1:
            self._in_h1 = False
            self._h1_done = True
            self.h1 = " ".join("".join(self._h1).split()) or None

    def handle_data(self, data):
        if self._in_title:
            self._title.append(data)
        if self._in_h1:
            self._h1.append(data)
        if self._skip_depth == 0:
            self.text_words += len(data.split())


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
    p = PageParser(url)
    try:
        p.feed(html)
    except Exception:
        pass
    haystack = " ".join(filter(None, [p.title, p.h1])).lower()
    title_h1_error = any(ph in haystack for ph in ERROR_PHRASES)
    return {"title": p.title, "h1": p.h1, "word_count": p.text_words,
            "error_phrase_in_title_or_h1": title_h1_error}, p.links


def probe_missing(site):
    """Request a definitely-missing URL to learn the site's not-found behavior."""
    test = urllib.parse.urljoin(site.rstrip("/") + "/",
                                "claude-soft404-probe-" + uuid.uuid4().hex[:12])
    status, final_url, html = fetch(test)
    info = {"url": test, "status": status, "final_url": final_url,
            "title": None, "word_count": 0}
    if html:
        a, _l = analyze(final_url, html)
        info["title"] = a["title"]
        info["word_count"] = a["word_count"]
    print(f"  missing-page probe [{status}] {test}", file=sys.stderr)
    return info


def extract_from_cache(cache_path):
    """Pure: turn a shared page cache (from fetch_pages.py) into a soft-404 inventory.

    Parses the cached HTML for the page signals this audit needs. The single
    missing-page probe is left to the caller (it is one request, not a crawl).
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
                          "h1": None, "word_count": 0,
                          "error_phrase_in_title_or_h1": False}
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
                          "h1": None, "word_count": 0,
                          "error_phrase_in_title_or_h1": False}
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
    ap = argparse.ArgumentParser(description="Capture page signals to detect soft 404s.")
    ap.add_argument("source", nargs="?")
    ap.add_argument("--from-cache",
                    help="Extract from a shared page cache produced by fetch_pages.py (no crawl)")
    ap.add_argument("--max-pages", type=int, default=500)
    ap.add_argument("--output", default="soft404_inventory.json")
    ap.add_argument("--url-list", action="store_true")
    args = ap.parse_args()

    probe = None
    if args.from_cache:
        site, pages = extract_from_cache(args.from_cache)
        if site.startswith(("http://", "https://")):
            origin = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(site))
            probe = probe_missing(origin)
    elif not args.source:
        ap.error("provide a source, or --from-cache page_cache.json")
    elif args.url_list:
        with open(args.source, encoding="utf-8") as f:
            urls = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        site, pages = args.source, collect(urls[: args.max_pages], args.max_pages)
        if urls:
            origin = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(urls[0]))
            probe = probe_missing(origin)
    else:
        start = args.source.rstrip("/")
        seeds = pages_from_sitemap(start) or [start]
        site, pages = args.source, collect(seeds[: args.max_pages], args.max_pages,
                                           crawl_host=norm_host(start))
        probe = probe_missing(start)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"site": site, "pages": pages, "missing_probe": probe},
                  f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(pages)} pages to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
