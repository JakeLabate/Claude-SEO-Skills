#!/usr/bin/env python3
"""Crawl an HTTPS site and inventory every subresource and its protocol.

Usage:
    python3 extract_resources.py https://example.com [--max-pages 500] [--output resource_inventory.json]
    python3 extract_resources.py urls.txt --url-list [--output resource_inventory.json]

For each crawled page it records the page URL/status and every subresource it
loads or links to — scripts, stylesheets, images, iframes, media, embeds, and
form actions — with the tag, attribute, and the (resolved) URL's scheme. The
auditor uses this to find mixed content (http resources on an https page).

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

USER_AGENT = "MixedContentAuditBot/1.0 (+claude-skill)"
TIMEOUT = 15

# tag -> attribute that holds a subresource URL, and whether it is "active"
# (executed/applied; browsers block insecure active content) or "passive".
RESOURCE_ATTRS = {
    "script": ("src", "active"),
    "link": ("href", "active"),       # stylesheets / preloads (rel-checked below)
    "iframe": ("src", "active"),
    "embed": ("src", "active"),
    "object": ("data", "active"),
    "img": ("src", "passive"),
    "audio": ("src", "passive"),
    "video": ("src", "passive"),
    "source": ("src", "passive"),
    "track": ("src", "passive"),
    "form": ("action", "form"),
}


class ResourceParser(HTMLParser):
    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.resources = []  # {tag, attr, url, scheme, kind}
        self.links = []

    def _record(self, tag, attr, value, kind):
        if not value:
            return
        resolved = urllib.parse.urljoin(self.base_url, value.strip())
        scheme = urllib.parse.urlparse(resolved).scheme
        protocol_relative = value.strip().startswith("//")
        self.resources.append({
            "tag": tag, "attr": attr, "url": resolved, "scheme": scheme,
            "kind": kind, "protocol_relative": protocol_relative})

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in RESOURCE_ATTRS:
            attr, kind = RESOURCE_ATTRS[tag]
            if tag == "link":
                rel = (a.get("rel") or "").lower()
                # Only stylesheets/imports are active; icons/manifests are passive-ish.
                kind = "active" if "stylesheet" in rel else "passive"
                if not any(r in rel for r in ("stylesheet", "preload", "icon",
                                              "manifest", "prefetch", "preconnect")):
                    return
            self._record(tag, attr, a.get(attr), kind)
        if tag == "a" and a.get("href"):
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


def collect(urls, max_pages, crawl_host=None):
    pages, queue, seen = {}, deque(urls), set(urls)
    while queue and len(pages) < max_pages:
        url = queue.popleft()
        status, final_url, html = fetch(url)
        print(f"[{status}] {url}", file=sys.stderr)
        if html is None:
            pages[url] = {"status": status, "final_url": final_url, "resources": []}
            continue
        parser = ResourceParser(final_url)
        try:
            parser.feed(html)
        except Exception:
            pass
        pages[url] = {"status": status, "final_url": final_url,
                      "resources": parser.resources}
        if crawl_host:
            for link in parser.links:
                if norm_host(link) == crawl_host and link not in seen:
                    seen.add(link)
                    queue.append(link)
    return pages


def main():
    ap = argparse.ArgumentParser(description="Inventory subresources and their protocols.")
    ap.add_argument("source")
    ap.add_argument("--max-pages", type=int, default=500)
    ap.add_argument("--output", default="resource_inventory.json")
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

    total = sum(len(p["resources"]) for p in pages.values())
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"site": args.source, "pages": pages}, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(pages)} pages, {total} resource references to {args.output}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
