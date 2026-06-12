#!/usr/bin/env python3
"""Crawl a website and build an internal link graph as JSON.

Usage:
    python3 crawl_links.py https://example.com [--max-pages 500] [--max-depth 5] [--output link_graph.json]

Output JSON schema:
{
  "site": "https://example.com",
  "pages": {
    "<url>": {
      "status": 200,
      "depth": 1,
      "title": "...",
      "canonical": "<url or null>",
      "meta_robots": "<content or null>",
      "links": [
        {"target": "<url>", "anchor": "...", "rel": "nofollow|null", "location": "nav|footer|content"}
      ]
    }
  },
  "statuses": {"<url>": 200}   # status of every linked URL, including non-crawled targets
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

USER_AGENT = "InternalLinkAuditBot/1.0 (+claude-skill)"
TIMEOUT = 15


class LinkParser(HTMLParser):
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.links = []
        self.title = None
        self.canonical = None
        self.meta_robots = None
        self._in_title = False
        self._current = None  # link being captured
        self._anchor_parts = []
        self._context = []  # nav/footer nesting

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("nav", "footer"):
            self._context.append(tag)
        elif tag == "title":
            self._in_title = True
        elif tag == "link" and a.get("rel", "").lower() == "canonical" and a.get("href"):
            self.canonical = urllib.parse.urljoin(self.base_url, a["href"])
        elif tag == "meta" and a.get("name", "").lower() == "robots":
            self.meta_robots = a.get("content")
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
                "location": location,
            }
            self._anchor_parts = []
        elif tag == "img" and self._current is not None and a.get("alt"):
            self._anchor_parts.append(a["alt"])

    def handle_endtag(self, tag):
        if tag in ("nav", "footer") and self._context and self._context[-1] == tag:
            self._context.pop()
        elif tag == "title":
            self._in_title = False
        elif tag == "a" and self._current is not None:
            self._current["anchor"] = " ".join(" ".join(self._anchor_parts).split())
            self.links.append(self._current)
            self._current = None

    def handle_data(self, data):
        if self._in_title:
            self.title = (self.title or "") + data.strip()
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


def same_host(url, host):
    return urllib.parse.urlparse(url).netloc.lower().lstrip("www.") == host


def main():
    ap = argparse.ArgumentParser(description="Crawl a site and build an internal link graph.")
    ap.add_argument("start_url")
    ap.add_argument("--max-pages", type=int, default=500)
    ap.add_argument("--max-depth", type=int, default=5)
    ap.add_argument("--output", default="link_graph.json")
    args = ap.parse_args()

    start = args.start_url.rstrip("/")
    host = urllib.parse.urlparse(start).netloc.lower().lstrip("www.")
    pages, statuses = {}, {}
    queue = deque([(start, 0)])
    seen = {start}

    while queue and len(pages) < args.max_pages:
        url, depth = queue.popleft()
        status, final_url, html = fetch(url)
        statuses[url] = status
        print(f"[{status}] depth={depth} {url}", file=sys.stderr)

        page = {"status": status, "depth": depth, "title": None,
                "canonical": None, "meta_robots": None, "links": []}
        if html:
            parser = LinkParser(final_url)
            try:
                parser.feed(html)
            except Exception:
                pass
            page.update(title=parser.title, canonical=parser.canonical,
                        meta_robots=parser.meta_robots)
            for link in parser.links:
                if not same_host(link["target"], host):
                    continue
                page["links"].append(link)
                t = link["target"]
                if t not in seen and depth + 1 <= args.max_depth:
                    seen.add(t)
                    queue.append((t, depth + 1))
        pages[url] = page

    # Resolve statuses for linked-but-uncrawled targets
    linked = {l["target"] for p in pages.values() for l in p["links"]}
    for t in sorted(linked - set(statuses)):
        status, _, _ = fetch(t)
        statuses[t] = status
        print(f"[{status}] (status-check) {t}", file=sys.stderr)

    with open(args.output, "w") as f:
        json.dump({"site": start, "pages": pages, "statuses": statuses}, f, indent=2)
    print(f"Wrote {len(pages)} pages, {len(statuses)} URL statuses to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
