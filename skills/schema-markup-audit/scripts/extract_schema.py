#!/usr/bin/env python3
"""Crawl a website (or scan local HTML files) and extract structured data into a JSON inventory.

Usage:
    python3 extract_schema.py https://example.com [--max-pages 200] [--output schema_inventory.json]
    python3 extract_schema.py ./site-folder --local [--output schema_inventory.json]
    python3 extract_schema.py urls.txt --url-list [--output schema_inventory.json]

Output JSON schema:
{
  "site": "https://example.com",
  "pages": {
    "<url>": {
      "status": 200,
      "title": "...",
      "canonical": "<url or null>",
      "meta_robots": "<content or null>",
      "schema_blocks": [
        {"format": "json-ld", "types": ["Product"], "data": {...}},
        {"format": "microdata", "types": ["Offer"], "data": {...}},
        {"format": "rdfa", "types": ["Article"], "data": {...}}
      ],
      "jsonld_errors": [
        {"block_index": 0, "error": "Expecting value: line 14 column 3 (char 200)", "snippet": "..."}
      ]
    }
  }
}

Uses only the Python standard library.
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import deque
from html.parser import HTMLParser

USER_AGENT = "SchemaMarkupAuditBot/1.0 (+claude-skill)"
TIMEOUT = 15


def extract_types(data):
    """Collect all @type values from a parsed JSON-LD object."""
    types = []

    def walk(node):
        if isinstance(node, dict):
            t = node.get("@type")
            if isinstance(t, str):
                types.append(t)
            elif isinstance(t, list):
                types.extend(x for x in t if isinstance(x, str))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    return types


class SchemaParser(HTMLParser):
    """Extract JSON-LD blocks, Microdata, RDFa, page links, and metadata."""

    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title = None
        self.canonical = None
        self.meta_robots = None
        self.links = []
        self.jsonld_raw = []  # raw text of each ld+json script
        self._in_jsonld = False
        self._jsonld_parts = []
        self._in_title = False
        # Microdata
        self.microdata_items = []  # top-level items
        self._md_stack = []  # (item_dict, opening_tag, depth_of_same_tag)
        self._md_text_target = None  # (item, prop) capturing text content
        self._md_text_parts = []
        # RDFa
        self.rdfa_items = []
        self._rdfa_stack = []  # (item_dict, opening_tag, depth_of_same_tag)
        self._rdfa_text_target = None
        self._rdfa_text_parts = []
        self._elem_depth = 0  # depth of open non-void elements

    # --- helpers -------------------------------------------------------
    def _set_prop(self, item, name, value):
        if name in item:
            existing = item[name]
            if isinstance(existing, list):
                existing.append(value)
            else:
                item[name] = [existing, value]
        else:
            item[name] = value

    VOID_TAGS = frozenset((
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    ))

    # --- HTMLParser hooks ----------------------------------------------
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        is_void = tag in self.VOID_TAGS
        if not is_void:
            self._elem_depth += 1

        if tag == "script" and (a.get("type") or "").strip().lower() == "application/ld+json":
            self._in_jsonld = True
            self._jsonld_parts = []
            return
        if tag == "title":
            self._in_title = True
        elif tag == "link" and (a.get("rel") or "").lower() == "canonical" and a.get("href"):
            self.canonical = urllib.parse.urljoin(self.base_url, a["href"])
        elif tag == "meta" and (a.get("name") or "").lower() == "robots":
            self.meta_robots = a.get("content")
        elif tag == "a" and a.get("href"):
            href = a["href"].strip()
            if not href.startswith(("mailto:", "tel:", "javascript:", "#")):
                target = urllib.parse.urljoin(self.base_url, href)
                self.links.append(urllib.parse.urldefrag(target)[0])

        # --- Microdata ---
        if "itemscope" in a:
            item = {"@type": (a.get("itemtype") or "").rsplit("/", 1)[-1] or None}
            if a.get("itemid"):
                item["@id"] = a["itemid"]
            prop = a.get("itemprop")
            if self._md_stack and prop:
                parent = self._md_stack[-1][0]
                self._set_prop(parent, prop, item)
            else:
                self.microdata_items.append(item)
            if not is_void:
                self._md_stack.append((item, self._elem_depth))
        elif a.get("itemprop") and self._md_stack:
            item = self._md_stack[-1][0]
            prop = a["itemprop"]
            value = None
            if tag == "meta":
                value = a.get("content")
            elif tag in ("img", "audio", "video", "embed", "iframe", "source"):
                value = a.get("src")
            elif tag in ("a", "area", "link"):
                value = a.get("href")
            elif tag == "time":
                value = a.get("datetime")
            elif tag == "data":
                value = a.get("value")
            if value is not None:
                if tag in ("a", "area", "link", "img", "audio", "video", "embed", "iframe", "source"):
                    value = urllib.parse.urljoin(self.base_url, value)
                self._set_prop(item, prop, value)
            else:
                self._md_text_target = (item, prop)
                self._md_text_parts = []

        # --- RDFa (typeof/property with vocab or schema.org prefix) ---
        if a.get("typeof"):
            rdfa_item = {"@type": a["typeof"].rsplit("/", 1)[-1].rsplit(":", 1)[-1]}
            prop = a.get("property")
            if self._rdfa_stack and prop:
                parent = self._rdfa_stack[-1][0]
                self._set_prop(parent, prop.rsplit(":", 1)[-1], rdfa_item)
            else:
                self.rdfa_items.append(rdfa_item)
            if not is_void:
                self._rdfa_stack.append((rdfa_item, self._elem_depth))
        elif a.get("property") and self._rdfa_stack:
            item = self._rdfa_stack[-1][0]
            prop = a["property"].rsplit(":", 1)[-1].rsplit("/", 1)[-1]
            value = a.get("content") or a.get("href") or a.get("src") or a.get("datetime")
            if value is not None:
                self._set_prop(item, prop, value)
            else:
                self._rdfa_text_target = (item, prop)
                self._rdfa_text_parts = []

    def handle_endtag(self, tag):
        if tag == "script" and self._in_jsonld:
            self._in_jsonld = False
            self.jsonld_raw.append("".join(self._jsonld_parts))
        elif tag == "title":
            self._in_title = False
        if self._md_text_target is not None:
            item, prop = self._md_text_target
            self._set_prop(item, prop, "".join(self._md_text_parts).strip())
            self._md_text_target = None
        if self._rdfa_text_target is not None:
            item, prop = self._rdfa_text_target
            self._set_prop(item, prop, "".join(self._rdfa_text_parts).strip())
            self._rdfa_text_target = None
        if tag not in self.VOID_TAGS:
            while self._md_stack and self._md_stack[-1][1] >= self._elem_depth:
                self._md_stack.pop()
            while self._rdfa_stack and self._rdfa_stack[-1][1] >= self._elem_depth:
                self._rdfa_stack.pop()
            self._elem_depth = max(0, self._elem_depth - 1)

    def handle_data(self, data):
        if self._in_jsonld:
            self._jsonld_parts.append(data)
        elif self._in_title and self.title is None:
            self.title = data.strip() or None
        if self._md_text_target is not None:
            self._md_text_parts.append(data)
        if self._rdfa_text_target is not None:
            self._rdfa_text_parts.append(data)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            ctype = resp.headers.get("Content-Type", "")
            if "html" not in ctype and "xml" not in ctype:
                return resp.status, None
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return 0, None


def pages_from_sitemap(site):
    status, body = fetch(urllib.parse.urljoin(site, "/sitemap.xml"))
    if status != 200 or not body:
        return []
    urls = []
    try:
        root = ET.fromstring(body)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        for loc in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
            urls.append(loc.text.strip())
    except ET.ParseError:
        return []
    return urls


def parse_page(url, html):
    parser = SchemaParser(url)
    try:
        parser.feed(html)
    except Exception:
        pass

    blocks = []
    errors = []
    for i, raw in enumerate(parser.jsonld_raw):
        text = raw.strip()
        if not text:
            errors.append({"block_index": i, "error": "empty JSON-LD block", "snippet": ""})
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            errors.append({"block_index": i, "error": str(e), "snippet": text[:200]})
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and "@graph" in item:
                for node in item["@graph"]:
                    blocks.append({"format": "json-ld", "types": extract_types(node), "data": node})
            else:
                blocks.append({"format": "json-ld", "types": extract_types(item), "data": item})

    for item in parser.microdata_items:
        if item.get("@type"):
            blocks.append({"format": "microdata", "types": extract_types(item), "data": item})
    for item in parser.rdfa_items:
        if item.get("@type"):
            blocks.append({"format": "rdfa", "types": extract_types(item), "data": item})

    return {
        "title": parser.title,
        "canonical": parser.canonical,
        "meta_robots": parser.meta_robots,
        "schema_blocks": blocks,
        "jsonld_errors": errors,
    }, parser.links


def extract_from_cache(cache_path):
    """Pure: turn a shared page cache (from fetch_pages.py) into a schema inventory.

    No network — parses the cached HTML for exactly the fields this audit needs.
    """
    with open(cache_path, encoding="utf-8") as f:
        cache = json.load(f)
    pages = {}
    for url, page in cache.get("pages", {}).items():
        html = page.get("html")
        status = page.get("status", 0)
        if not html:
            pages[url] = {"status": status, "title": None, "canonical": None,
                          "meta_robots": None, "schema_blocks": [], "jsonld_errors": []}
            continue
        info, _links = parse_page(page.get("final_url") or url, html)
        info["status"] = status
        pages[url] = info
    return cache.get("site", cache_path), pages


def crawl(site, max_pages):
    host = urllib.parse.urlparse(site).netloc
    seeds = pages_from_sitemap(site) or [site]
    queue = deque(seeds[:max_pages])
    seen = set(queue)
    pages = {}
    while queue and len(pages) < max_pages:
        url = queue.popleft()
        status, html = fetch(url)
        if html is None:
            pages[url] = {"status": status, "title": None, "canonical": None,
                          "meta_robots": None, "schema_blocks": [], "jsonld_errors": []}
            continue
        info, links = parse_page(url, html)
        info["status"] = status
        pages[url] = info
        for link in links:
            if urllib.parse.urlparse(link).netloc == host and link not in seen:
                seen.add(link)
                queue.append(link)
        sys.stderr.write(f"\rScanned {len(pages)} pages...")
    sys.stderr.write("\n")
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
        status, html = fetch(url)
        if html is None:
            pages[url] = {"status": status, "title": None, "canonical": None,
                          "meta_robots": None, "schema_blocks": [], "jsonld_errors": []}
            continue
        info, _links = parse_page(url, html)
        info["status"] = status
        pages[url] = info
    return pages


def main():
    ap = argparse.ArgumentParser(description="Extract structured data from a site into a JSON inventory")
    ap.add_argument("source", nargs="?",
                    help="Site root URL, local folder (--local), or URL list file (--url-list)")
    ap.add_argument("--from-cache",
                    help="Extract from a shared page cache produced by fetch_pages.py (no network)")
    ap.add_argument("--max-pages", type=int, default=200)
    ap.add_argument("--output", default="schema_inventory.json")
    ap.add_argument("--local", action="store_true", help="Treat source as a local folder of HTML files")
    ap.add_argument("--url-list", action="store_true", help="Treat source as a text file of URLs")
    args = ap.parse_args()

    if args.from_cache:
        site, pages = extract_from_cache(args.from_cache)
    elif not args.source:
        ap.error("provide a source, or --from-cache page_cache.json")
    elif args.local:
        site, pages = args.source, scan_local(args.source)
    elif args.url_list:
        site, pages = args.source, scan_url_list(args.source, args.max_pages)
    else:
        site, pages = args.source, crawl(args.source, args.max_pages)

    inventory = {"site": site, "pages": pages}
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(inventory, f, indent=2, ensure_ascii=False)
    blocks = sum(len(p["schema_blocks"]) for p in pages.values())
    print(f"Scanned {len(pages)} pages, found {blocks} schema blocks. Wrote {args.output}")


if __name__ == "__main__":
    main()
