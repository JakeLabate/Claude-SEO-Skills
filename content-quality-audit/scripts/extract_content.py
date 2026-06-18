#!/usr/bin/env python3
"""Crawl a site and capture content-quality signals (length, ratio, dedupe sigs).

Usage:
    python3 extract_content.py https://example.com [--max-pages 500] [--output content_inventory.json]
    python3 extract_content.py urls.txt --url-list [--output content_inventory.json]

For each page it records status, title, first H1, visible word count, the
text-to-HTML ratio, whether the page declares noindex, an exact content hash, and
a 32-value MinHash signature of its word shingles so the auditor can find exact
and near-duplicate bodies cheaply (no pairwise text comparison, no dependencies).

Uses only the Python standard library.
"""

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import deque
from html.parser import HTMLParser

USER_AGENT = "ContentQualityAuditBot/1.0 (+claude-skill)"
TIMEOUT = 15
NUM_HASHES = 32
SHINGLE = 4
MASK = (1 << 32) - 1
SEEDS = [0x9E3779B1 * (i + 1) & MASK for i in range(NUM_HASHES)]
SKIP_TEXT_TAGS = {"script", "style", "noscript", "template", "svg"}


class ContentParser(HTMLParser):
    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title = None
        self.h1 = None
        self.text_chars = 0
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
        elif tag == "meta" and (a.get("name") or "").lower() == "robots":
            self.meta_robots = a.get("content")
        elif tag == "a" and a.get("href"):
            href = a["href"].strip()
            if not href.startswith(("mailto:", "tel:", "javascript:", "#")):
                self.links.append(
                    urllib.parse.urldefrag(urllib.parse.urljoin(self.base_url, href))[0])

    meta_robots = None

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
            stripped = data.strip()
            if stripped:
                self.text_chars += len(stripped)
                self.tokens.extend(re.findall(r"[a-z0-9']+", stripped.lower()))


def minhash(tokens):
    if len(tokens) < SHINGLE:
        shingles = {" ".join(tokens)} if tokens else set()
    else:
        shingles = {" ".join(tokens[i:i + SHINGLE])
                    for i in range(len(tokens) - SHINGLE + 1)}
    if not shingles:
        return None
    hashed = [int(hashlib.md5(s.encode()).hexdigest()[:8], 16) for s in shingles]
    return [min((h ^ seed) & MASK for h in hashed) for seed in SEEDS]


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
    p = ContentParser(url)
    try:
        p.feed(html)
    except Exception:
        pass
    word_count = len(p.tokens)
    ratio = round(p.text_chars / len(html), 4) if html else 0
    norm_text = " ".join(p.tokens)
    info = {
        "title": p.title, "h1": p.h1, "word_count": word_count,
        "text_to_html_ratio": ratio,
        "noindex": "noindex" in (p.meta_robots or "").lower(),
        "content_hash": hashlib.md5(norm_text.encode()).hexdigest() if norm_text else None,
        "minhash": minhash(p.tokens),
    }
    return info, p.links


def collect(urls, max_pages, crawl_host=None):
    pages, queue, seen = {}, deque(urls), set(urls)
    while queue and len(pages) < max_pages:
        url = queue.popleft()
        status, final_url, html = fetch(url)
        print(f"[{status}] {url}", file=sys.stderr)
        if html is None:
            pages[url] = {"status": status, "final_url": final_url, "title": None,
                          "h1": None, "word_count": 0, "text_to_html_ratio": 0,
                          "noindex": False, "content_hash": None, "minhash": None}
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
    ap = argparse.ArgumentParser(description="Capture content-quality signals for a site.")
    ap.add_argument("source")
    ap.add_argument("--max-pages", type=int, default=500)
    ap.add_argument("--output", default="content_inventory.json")
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

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"site": args.source, "pages": pages}, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(pages)} pages to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
