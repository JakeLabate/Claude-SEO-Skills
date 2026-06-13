#!/usr/bin/env python3
"""Crawl a website and gather architecture signals into a JSON inventory.

Usage:
    python3 crawl_architecture.py https://example.com [--max-pages 500] [--max-depth 10] [--output architecture_inventory.json]

Gathers:
- Host/protocol variant probe (http/https x www/non-www): status + redirect target of each
- robots.txt: status, parsed user-agent groups (Disallow/Allow), Sitemap: directives, raw text
- XML sitemaps: every <loc>, following sitemap index files; total URL count
- Per crawled page: requested URL, final URL, status, redirect chain, click depth,
  scheme/host/path/query, path-segment count, canonical, meta robots, title,
  and the raw resolved internal link targets (for URL-form consistency checks)

Output JSON schema:
{
  "site": "https://example.com",
  "canonical_host": "https://example.com",
  "host_variants": {"<variant>": {"status": 301, "final_url": "..."}},
  "robots_txt": {"found": true, "status": 200, "sitemaps": [...],
                 "rules": [{"agent": "*", "disallow": [...], "allow": [...]}], "raw": "..."},
  "sitemap": {"found": true, "sources": [...], "url_count": 120, "urls": [...], "errors": [...]},
  "pages_crawled": 100,
  "pages": {
    "<requested url>": {
      "status": 200, "final_url": "...", "redirected": false, "redirect_chain": [],
      "depth": 0, "scheme": "https", "host": "example.com", "path": "/x", "query": "",
      "segments": 1, "canonical": "...|null", "meta_robots": "...|null", "title": "...|null",
      "links": ["<raw resolved internal target>", ...]
    }
  }
}

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

USER_AGENT = "SiteArchitectureAuditBot/1.0 (+claude-skill)"
TIMEOUT = 15
MAX_SITEMAPS = 50


class PageParser(HTMLParser):
    """Extract title, canonical, meta robots, and same-document link hrefs."""

    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title = None
        self.canonical = None
        self.meta_robots = None
        self.links = []
        self._in_title = False
        self._title_parts = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self._in_title = True
            self._title_parts = []
        elif tag == "link" and (a.get("rel") or "").lower() == "canonical" and a.get("href"):
            self.canonical = urllib.parse.urljoin(self.base_url, a["href"].strip())
        elif tag == "meta" and (a.get("name") or "").lower() == "robots":
            self.meta_robots = a.get("content")
        elif tag == "a" and a.get("href"):
            href = a["href"].strip()
            if href.startswith(("mailto:", "tel:", "javascript:", "#")):
                return
            target = urllib.parse.urljoin(self.base_url, href)
            self.links.append(urllib.parse.urldefrag(target)[0])

    def handle_endtag(self, tag):
        if tag == "title" and self._in_title:
            self._in_title = False
            self.title = " ".join("".join(self._title_parts).split()) or None

    def handle_data(self, data):
        if self._in_title:
            self._title_parts.append(data)


def norm_host(host):
    host = host.lower()
    return host[4:] if host.startswith("www.") else host


def fetch(url, follow=True):
    """Return (status, final_url, html_or_none, redirect_chain).

    redirect_chain is a list of {"from": url, "status": code, "to": location}.
    """
    chain = []

    class ChainRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            chain.append({"from": req.full_url, "status": code, "to": newurl})
            if not follow:
                return None
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    opener = urllib.request.build_opener(ChainRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with opener.open(req, timeout=TIMEOUT) as resp:
            ctype = resp.headers.get("Content-Type", "")
            body = None
            if "html" in ctype or "xml" in ctype:
                body = resp.read(2_000_000).decode("utf-8", errors="replace")
            return resp.status, resp.geturl(), body, chain
    except urllib.error.HTTPError as e:
        if not follow and e.code in range(300, 400):
            loc = e.headers.get("Location")
            final = urllib.parse.urljoin(url, loc) if loc else url
            return e.code, final, None, chain
        return e.code, url, None, chain
    except Exception:
        return 0, url, None, chain  # 0 = network/connection error


def probe_host_variants(start):
    """Probe http/https x www/non-www; return dict and the chosen canonical host."""
    parsed = urllib.parse.urlparse(start)
    bare = norm_host(parsed.netloc)
    variants = {}
    for scheme in ("https", "http"):
        for host in (bare, "www." + bare):
            root = f"{scheme}://{host}/"
            status, final_url, _body, _chain = fetch(root, follow=False)
            variants[f"{scheme}://{host}"] = {"status": status, "final_url": final_url}

    # Canonical host = the 200 variant that the others redirect toward, preferring https.
    live_200 = [v for v, info in variants.items()
                if info["status"] == 200]
    canonical_host = None
    for pref in (f"https://{bare}", f"https://www.{bare}",
                 f"http://{bare}", f"http://www.{bare}"):
        if pref in variants and variants[pref]["status"] == 200:
            canonical_host = pref
            break
    if canonical_host is None and live_200:
        canonical_host = live_200[0]
    if canonical_host is None:
        canonical_host = f"{parsed.scheme}://{parsed.netloc}"
    return variants, canonical_host


def parse_robots(text):
    """Minimal robots.txt parse: groups of agents with allow/disallow, plus sitemaps.

    A run of consecutive User-agent lines shares one group. The first allow/disallow
    after a User-agent line closes the run, so the next User-agent starts a new group.
    """
    groups = []
    sitemaps = []
    current = None
    last_was_directive = False
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, _, value = line.partition(":")
        field = field.strip().lower()
        value = value.strip()
        if field == "sitemap":
            if value:
                sitemaps.append(value)
            continue
        if field == "user-agent":
            if current is None or last_was_directive:
                current = {"agents": [], "disallow": [], "allow": []}
                groups.append(current)
            current["agents"].append(value)
            last_was_directive = False
        elif field in ("disallow", "allow") and current is not None:
            current[field].append(value)
            last_was_directive = True
    flat = []
    for g in groups:
        for agent in g["agents"]:
            flat.append({"agent": agent, "disallow": list(g["disallow"]),
                         "allow": list(g["allow"])})
    return flat, sitemaps


def fetch_robots(canonical_host):
    url = canonical_host.rstrip("/") + "/robots.txt"
    status, _final, body, _chain = fetch(url, follow=True)
    if status != 200 or body is None:
        # Try a plain fetch in case content-type was not html/xml
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                status = resp.status
                body = resp.read(1_000_000).decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            return {"found": False, "status": e.code, "sitemaps": [], "rules": [], "raw": ""}
        except Exception:
            return {"found": False, "status": status, "sitemaps": [], "rules": [], "raw": ""}
    rules, sitemaps = parse_robots(body or "")
    return {"found": status == 200, "status": status, "sitemaps": sitemaps,
            "rules": rules, "raw": (body or "")[:20000]}


def collect_sitemap_urls(seed_sitemaps, canonical_host):
    """Follow sitemap index files and gather all page <loc> URLs."""
    SM_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    seeds = list(seed_sitemaps)
    if not seeds:
        seeds = [canonical_host.rstrip("/") + "/sitemap.xml"]
    seen = set()
    queue = deque(seeds)
    page_urls = []
    sources = []
    errors = []
    found_any = False
    while queue and len(seen) < MAX_SITEMAPS:
        sm_url = queue.popleft()
        if sm_url in seen:
            continue
        seen.add(sm_url)
        status, _final, body, _chain = fetch(sm_url, follow=True)
        if status != 200 or not body:
            # retry plain
            try:
                req = urllib.request.Request(sm_url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                    status = resp.status
                    body = resp.read(5_000_000).decode("utf-8", errors="replace")
            except Exception:
                errors.append({"sitemap": sm_url, "error": f"status {status}"})
                continue
        try:
            root = ET.fromstring(body)
        except ET.ParseError as e:
            errors.append({"sitemap": sm_url, "error": f"parse error: {e}"})
            continue
        found_any = True
        sources.append(sm_url)
        tag = root.tag.lower()
        if tag.endswith("sitemapindex"):
            for loc in root.iter(SM_NS + "loc"):
                if loc.text:
                    queue.append(loc.text.strip())
        else:  # urlset
            for loc in root.iter(SM_NS + "loc"):
                if loc.text:
                    page_urls.append(loc.text.strip())
    # Deduplicate while preserving order
    seen_u = set()
    deduped = []
    for u in page_urls:
        if u not in seen_u:
            seen_u.add(u)
            deduped.append(u)
    return {"found": found_any, "sources": sources, "url_count": len(deduped),
            "urls": deduped, "errors": errors}


def url_parts(url):
    p = urllib.parse.urlparse(url)
    path = p.path or "/"
    segments = [s for s in path.split("/") if s]
    return {"scheme": p.scheme, "host": p.netloc.lower(), "path": path,
            "query": p.query, "segments": len(segments)}


def main():
    ap = argparse.ArgumentParser(description="Crawl a site and gather architecture signals.")
    ap.add_argument("start_url")
    ap.add_argument("--max-pages", type=int, default=500)
    ap.add_argument("--max-depth", type=int, default=10)
    ap.add_argument("--output", default="architecture_inventory.json")
    args = ap.parse_args()

    start = args.start_url.rstrip("/")
    host = norm_host(urllib.parse.urlparse(start).netloc)

    print("Probing host/protocol variants...", file=sys.stderr)
    host_variants, canonical_host = probe_host_variants(start)
    print(f"Canonical host: {canonical_host}", file=sys.stderr)

    print("Fetching robots.txt...", file=sys.stderr)
    robots = fetch_robots(canonical_host)

    print("Collecting sitemap URLs...", file=sys.stderr)
    sitemap = collect_sitemap_urls(robots.get("sitemaps", []), canonical_host)
    print(f"Sitemap URLs found: {sitemap['url_count']}", file=sys.stderr)

    print("Crawling pages...", file=sys.stderr)
    pages = {}
    queue = deque([(start, 0)])
    seen = {start}
    while queue and len(pages) < args.max_pages:
        url, depth = queue.popleft()
        status, final_url, html, chain = fetch(url, follow=True)
        parts = url_parts(final_url if status < 400 else url)
        page = {
            "status": status,
            "final_url": final_url,
            "redirected": bool(chain),
            "redirect_chain": chain,
            "depth": depth,
            "scheme": parts["scheme"],
            "host": parts["host"],
            "path": parts["path"],
            "query": parts["query"],
            "segments": parts["segments"],
            "canonical": None,
            "meta_robots": None,
            "title": None,
            "links": [],
        }
        print(f"[{status}] depth={depth} {url}", file=sys.stderr)
        if html:
            parser = PageParser(final_url)
            try:
                parser.feed(html)
            except Exception:
                pass
            page["canonical"] = parser.canonical
            page["meta_robots"] = parser.meta_robots
            page["title"] = parser.title
            internal = []
            for target in parser.links:
                if not target.startswith(("http://", "https://")):
                    continue
                if norm_host(urllib.parse.urlparse(target).netloc) == host:
                    internal.append(target)
                    if target not in seen and depth + 1 <= args.max_depth:
                        seen.add(target)
                        queue.append((target, depth + 1))
            page["links"] = internal
        pages[url] = page

    inventory = {
        "site": start,
        "canonical_host": canonical_host,
        "host_variants": host_variants,
        "robots_txt": robots,
        "sitemap": sitemap,
        "pages_crawled": len(pages),
        "pages": pages,
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(inventory, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(pages)} pages to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
