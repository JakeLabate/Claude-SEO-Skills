#!/usr/bin/env python3
"""Resolve the full redirect chain for a set of URLs and record it as JSON.

Usage:
    python3 collect_redirects.py https://example.com [--max-pages 500] [--max-hops 10] [--output redirect_inventory.json]
    python3 collect_redirects.py sitemap.xml --sitemap [--output redirect_inventory.json]
    python3 collect_redirects.py urls.txt --url-list [--output redirect_inventory.json]

For every requested URL the script follows redirects one hop at a time (it never
lets urllib auto-follow) so it can record each individual hop, detect loops, and
flag downgrades to HTTP. It also inspects the final document for meta-refresh and
client-side (JavaScript) redirects, which search engines treat far worse than a
server 301.

Output JSON schema:
{
  "site": "<source>",
  "canonical_host": "https://example.com",   # only for crawl mode
  "pages": {
    "<requested url>": {
      "requested_url": "...",
      "hops": [{"url": "...", "status": 301, "location": "...", "scheme": "https", "host": "example.com"}],
      "chain_length": 1,                       # number of redirect hops
      "final_url": "...",
      "final_status": 200,
      "status_codes": [301],                   # distinct redirect codes in the chain
      "loop": false,
      "exceeded_max_hops": false,
      "scheme_changes": false,
      "host_changes": false,
      "downgrade_to_http": false,
      "drops_query": false,
      "meta_refresh": {"found": false, "delay": null, "url": null},
      "js_redirect": false,
      "final_canonical": "...|null"
    }
  }
}

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
from collections import deque
from html.parser import HTMLParser

USER_AGENT = "RedirectAuditBot/1.0 (+claude-skill)"
TIMEOUT = 15
SM_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"

META_REFRESH_RE = re.compile(r"""url\s*=\s*['"]?([^'">\s]+)""", re.IGNORECASE)
JS_REDIRECT_RE = re.compile(
    r"""(?:window\.)?location(?:\.href|\.replace\s*\(|\.assign\s*\(|\s*=)\s*['"]([^'"]+)""",
    re.IGNORECASE,
)


class FinalPageParser(HTMLParser):
    """Extract canonical and meta-refresh from a final (200) document."""

    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.canonical = None
        self.meta_refresh = None  # (delay, url)
        self.links = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "link" and (a.get("rel") or "").lower() == "canonical" and a.get("href"):
            self.canonical = urllib.parse.urljoin(self.base_url, a["href"].strip())
        elif tag == "meta" and (a.get("http-equiv") or "").lower() == "refresh":
            content = a.get("content") or ""
            delay = content.split(";", 1)[0].strip()
            m = META_REFRESH_RE.search(content)
            url = urllib.parse.urljoin(self.base_url, m.group(1)) if m else None
            self.meta_refresh = (delay, url)
        elif tag == "a" and a.get("href"):
            href = a["href"].strip()
            if not href.startswith(("mailto:", "tel:", "javascript:", "#")):
                self.links.append(urllib.parse.urldefrag(urllib.parse.urljoin(self.base_url, href))[0])


def raw_fetch(url):
    """Fetch a single URL WITHOUT following redirects.

    Returns (status, location_or_none, body_or_none, content_type).
    """

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None  # never follow

    opener = urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with opener.open(req, timeout=TIMEOUT) as resp:
            ctype = resp.headers.get("Content-Type", "")
            body = None
            if "html" in ctype:
                body = resp.read(1_000_000).decode("utf-8", errors="replace")
            return resp.status, None, body, ctype
    except urllib.error.HTTPError as e:
        loc = e.headers.get("Location") if e.headers else None
        return e.code, loc, None, (e.headers.get("Content-Type", "") if e.headers else "")
    except Exception:
        return 0, None, None, ""  # 0 = network/connection error


def norm_host(host):
    host = host.lower()
    return host[4:] if host.startswith("www.") else host


def follow_chain(start_url, max_hops):
    hops = []
    current = start_url
    seen = {start_url}
    loop = False
    exceeded = False
    final_body = None
    final_status = 0
    final_url = start_url

    for _ in range(max_hops + 1):
        status, location, body, _ctype = raw_fetch(current)
        p = urllib.parse.urlparse(current)
        if 300 <= status < 400 and location:
            target = urllib.parse.urljoin(current, location.strip())
            hops.append({"url": current, "status": status, "location": target,
                         "scheme": p.scheme, "host": p.netloc.lower()})
            if target in seen:
                loop = True
                final_url, final_status = target, status
                break
            seen.add(target)
            current = target
        else:
            final_url, final_status, final_body = current, status, body
            break
    else:
        exceeded = True
        final_url, final_status = current, 0

    return hops, final_url, final_status, final_body, loop, exceeded


def analyze(start_url, max_hops):
    hops, final_url, final_status, final_body, loop, exceeded = follow_chain(start_url, max_hops)

    start_p = urllib.parse.urlparse(start_url)
    final_p = urllib.parse.urlparse(final_url)
    schemes = {h["scheme"] for h in hops} | {start_p.scheme, final_p.scheme}
    hosts = {norm_host(h["host"]) for h in hops} | {norm_host(start_p.netloc), norm_host(final_p.netloc)}
    downgrade = any(
        urllib.parse.urlparse(h["url"]).scheme == "https"
        and urllib.parse.urlparse(h["location"]).scheme == "http"
        for h in hops
    )
    drops_query = bool(start_p.query) and not final_p.query

    canonical = None
    meta_refresh = {"found": False, "delay": None, "url": None}
    js_redirect = False
    if final_body:
        parser = FinalPageParser(final_url)
        try:
            parser.feed(final_body)
        except Exception:
            pass
        canonical = parser.canonical
        if parser.meta_refresh:
            meta_refresh = {"found": True, "delay": parser.meta_refresh[0], "url": parser.meta_refresh[1]}
        js_redirect = bool(JS_REDIRECT_RE.search(final_body[:200_000]))

    return {
        "requested_url": start_url,
        "hops": hops,
        "chain_length": len(hops),
        "final_url": final_url,
        "final_status": final_status,
        "status_codes": sorted({h["status"] for h in hops}),
        "loop": loop,
        "exceeded_max_hops": exceeded,
        "scheme_changes": len(schemes) > 1,
        "host_changes": len(hosts) > 1,
        "downgrade_to_http": downgrade,
        "drops_query": drops_query,
        "meta_refresh": meta_refresh,
        "js_redirect": js_redirect,
        "final_canonical": canonical,
    }


def urls_from_sitemap(source):
    status, loc, body, _ = raw_fetch(source)
    if 300 <= status < 400 and loc:
        status, loc, body, _ = raw_fetch(urllib.parse.urljoin(source, loc))
    if status != 200 or not body:
        # raw_fetch only returns body for text/html; refetch xml plainly
        try:
            req = urllib.request.Request(source, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                body = resp.read(10_000_000).decode("utf-8", errors="replace")
        except Exception:
            return []
    urls, queue, seen = [], deque([body]), set()
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return []
    if root.tag.lower().endswith("sitemapindex"):
        children = [loc.text.strip() for loc in root.iter(SM_NS + "loc") if loc.text]
        for child in children:
            if child in seen:
                continue
            seen.add(child)
            try:
                req = urllib.request.Request(child, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                    sub = ET.fromstring(resp.read(10_000_000).decode("utf-8", errors="replace"))
                urls += [loc.text.strip() for loc in sub.iter(SM_NS + "loc") if loc.text]
            except Exception:
                continue
    else:
        urls = [loc.text.strip() for loc in root.iter(SM_NS + "loc") if loc.text]
    return urls


def crawl_urls(start, max_pages, max_hops):
    host = norm_host(urllib.parse.urlparse(start).netloc)
    pages = {}
    queue = deque([start])
    seen = {start}
    while queue and len(pages) < max_pages:
        url = queue.popleft()
        result = analyze(url, max_hops)
        pages[url] = result
        print(f"[{result['final_status']}] {result['chain_length']} hop(s) {url}", file=sys.stderr)
        # Discover more same-host links from the final page only when it resolved 200.
        if result["final_status"] == 200:
            _h, _f, _s, body, _l, _e = follow_chain(url, max_hops)
            if body:
                parser = FinalPageParser(result["final_url"])
                try:
                    parser.feed(body)
                except Exception:
                    pass
                for target in parser.links:
                    if not target.startswith(("http://", "https://")):
                        continue
                    if norm_host(urllib.parse.urlparse(target).netloc) == host and target not in seen:
                        seen.add(target)
                        queue.append(target)
    return pages


def main():
    ap = argparse.ArgumentParser(description="Resolve redirect chains for a set of URLs.")
    ap.add_argument("source", help="Site root URL, sitemap (--sitemap), or URL list file (--url-list)")
    ap.add_argument("--max-pages", type=int, default=500)
    ap.add_argument("--max-hops", type=int, default=10)
    ap.add_argument("--output", default="redirect_inventory.json")
    ap.add_argument("--sitemap", action="store_true", help="Treat source as a sitemap URL")
    ap.add_argument("--url-list", action="store_true", help="Treat source as a text file of URLs")
    args = ap.parse_args()

    canonical_host = None
    if args.url_list:
        with open(args.source, encoding="utf-8") as f:
            urls = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
        pages = {}
        for url in urls[: args.max_pages]:
            pages[url] = analyze(url, args.max_hops)
            print(f"[{pages[url]['final_status']}] {pages[url]['chain_length']} hop(s) {url}", file=sys.stderr)
    elif args.sitemap:
        urls = urls_from_sitemap(args.source)
        pages = {}
        for url in urls[: args.max_pages]:
            pages[url] = analyze(url, args.max_hops)
            print(f"[{pages[url]['final_status']}] {pages[url]['chain_length']} hop(s) {url}", file=sys.stderr)
    else:
        canonical_host = args.source.rstrip("/")
        pages = crawl_urls(canonical_host, args.max_pages, args.max_hops)

    out = {"site": args.source, "canonical_host": canonical_host, "pages": pages}
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    redirecting = sum(1 for p in pages.values() if p["chain_length"] > 0)
    print(f"Wrote {len(pages)} URLs ({redirecting} redirecting) to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
