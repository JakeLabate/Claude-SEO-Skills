#!/usr/bin/env python3
"""Crawl a website and build an external (outbound) link inventory as JSON.

Usage:
    python3 extract_external_links.py https://example.com [--max-pages 500] [--max-depth 5] [--output external_links.json]

Output JSON schema:
{
  "site": "https://example.com",
  "pages_crawled": 42,
  "links": [
    {
      "source": "<page url>",
      "target": "<external url>",
      "domain": "<target host>",
      "anchor": "...",
      "rel": "nofollow sponsored|null",
      "target_attr": "_blank|null",
      "location": "nav|footer|content"
    }
  ]
}

Uses only the Python standard library.
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from html.parser import HTMLParser

USER_AGENT = "ExternalLinkAuditBot/1.0 (+claude-skill)"
TIMEOUT = 15


class LinkParser(HTMLParser):
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.links = []
        self._current = None  # link being captured
        self._anchor_parts = []
        self._context = []  # nav/footer nesting

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("nav", "footer"):
            self._context.append(tag)
        elif tag == "a" and a.get("href"):
            href = a["href"].strip()
            if href.startswith(("mailto:", "tel:", "javascript:", "#")):
                return
            target = urllib.parse.urljoin(self.base_url, href)
            target = urllib.parse.urldefrag(target)[0]
            location = self._context[-1] if self._context else "content"
            self._current = {
                "target": target,
                "anchor": "",
                "rel": a.get("rel") or None,
                "target_attr": a.get("target") or None,
                "location": location,
            }
            self._anchor_parts = []
        elif tag == "img" and self._current is not None and a.get("alt"):
            self._anchor_parts.append(a["alt"])

    def handle_endtag(self, tag):
        if tag in ("nav", "footer") and self._context and self._context[-1] == tag:
            self._context.pop()
        elif tag == "a" and self._current is not None:
            self._current["anchor"] = " ".join(" ".join(self._anchor_parts).split())
            self.links.append(self._current)
            self._current = None

    def handle_data(self, data):
        if self._current is not None:
            self._anchor_parts.append(data)


def fetch(url):
    """Return (status, final_url, html_or_none)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            ctype = resp.headers.get("Content-Type", "")
            body = None
            if "text/html" in ctype:
                body = resp.read(2_000_000).decode("utf-8", errors="replace")
            return resp.status, resp.geturl(), body
    except urllib.error.HTTPError as e:
        return e.code, url, None
    except Exception:
        return 0, url, None  # 0 = network/connection error


def norm_host(url):
    host = urllib.parse.urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def external_in(source_url, final_url, html, host):
    """Return (external_link_records, internal_targets) parsed from one page."""
    parser = LinkParser(final_url)
    try:
        parser.feed(html)
    except Exception:
        pass
    external, internal = [], []
    for link in parser.links:
        target = link["target"]
        if not target.startswith(("http://", "https://")):
            continue
        if norm_host(target) == host:
            internal.append(target)
            continue
        external.append({"source": source_url, "domain": norm_host(target), **link})
    return external, internal


def extract_from_cache(cache_path):
    """Pure: collect external links from a shared page cache (from fetch_pages.py).

    No network — the link checking lives in check_external_links.py, which still
    probes the external URLs.
    """
    with open(cache_path, encoding="utf-8") as f:
        cache = json.load(f)
    pages = cache.get("pages", {})
    site = cache.get("site", cache_path)
    host = norm_host(site) if site.startswith(("http://", "https://")) else ""
    if not host:
        for page in pages.values():
            if page.get("final_url", "").startswith(("http://", "https://")):
                host = norm_host(page["final_url"])
                break
    external_links, crawled = [], 0
    for url, page in pages.items():
        html = page.get("html")
        if not html:
            continue
        crawled += 1
        out, _internal = external_in(url, page.get("final_url") or url, html, host)
        external_links.extend(out)
    return site, crawled, external_links


def main():
    ap = argparse.ArgumentParser(description="Crawl a site and collect external links.")
    ap.add_argument("start_url", nargs="?")
    ap.add_argument("--from-cache",
                    help="Extract from a shared page cache produced by fetch_pages.py (no network)")
    ap.add_argument("--max-pages", type=int, default=500)
    ap.add_argument("--max-depth", type=int, default=5)
    ap.add_argument("--output", default="external_links.json")
    args = ap.parse_args()

    if args.from_cache:
        start, pages_crawled, external_links = extract_from_cache(args.from_cache)
    elif not args.start_url:
        ap.error("provide a start_url, or --from-cache page_cache.json")
    else:
        start = args.start_url.rstrip("/")
        host = norm_host(start)
        external_links = []
        crawled = set()
        queue = deque([(start, 0)])
        seen = {start}

        while queue and len(crawled) < args.max_pages:
            url, depth = queue.popleft()
            status, final_url, html = fetch(url)
            crawled.add(url)
            print(f"[{status}] depth={depth} {url}", file=sys.stderr)

            if not html:
                continue
            out, internal = external_in(url, final_url, html, host)
            external_links.extend(out)
            for target in internal:
                if target not in seen and depth + 1 <= args.max_depth:
                    seen.add(target)
                    queue.append((target, depth + 1))
        pages_crawled = len(crawled)

    with open(args.output, "w") as f:
        json.dump({"site": start, "pages_crawled": pages_crawled,
                   "links": external_links}, f, indent=2)
    print(f"Wrote {len(external_links)} external links from {pages_crawled} pages to {args.output}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
