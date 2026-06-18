#!/usr/bin/env python3
"""Collect Core Web Vitals signals for a set of pages into a JSON inventory.

Usage:
    python3 collect_vitals.py https://example.com [--max-pages 50] [--output vitals_inventory.json]
    python3 collect_vitals.py https://example.com/sitemap.xml --sitemap [--max-pages 50]
    python3 collect_vitals.py urls.txt --url-list [--max-pages 50]

    # Add real field + lab data from Google PageSpeed Insights (CrUX + Lighthouse):
    python3 collect_vitals.py https://example.com --psi --psi-strategy mobile [--psi-key YOUR_KEY]

Two layers of data are collected:

1. LAB PROXIES (always, stdlib only) — static signals that correlate with the
   Core Web Vitals without a real browser: measured TTFB, HTML transfer size and
   compression, render-blocking CSS/JS in the head, total subresource weight by
   type, request counts, image dimension/lazy-loading hygiene (CLS / LCP), an
   approximate DOM node count, third-party origins, and resource hints present.

2. PSI FIELD + LAB (optional, --psi) — Google PageSpeed Insights returns real
   CrUX field metrics (LCP, CLS, INP, FCP, TTFB) and a Lighthouse lab score.
   This is the authoritative Core Web Vitals source; the lab proxies above are a
   fast, browserless approximation for when PSI is unavailable or rate-limited.

Output JSON schema (per page):
{
  "status": 200, "final_url": "...", "ttfb_ms": 180, "fetch_ms": 540,
  "html_bytes": 41234, "html_compressed": true, "html_cache_control": "...|null",
  "render_blocking_css": 3, "render_blocking_js": 2, "total_scripts": 11,
  "inline_script_bytes": 8000, "inline_style_bytes": 1200,
  "image_count": 24, "images_missing_dimensions": 9, "images_no_lazy": 20,
  "lcp_image_lazy": true, "dom_nodes": 1640,
  "resource_hints": {"preconnect": 1, "dns_prefetch": 0, "preload": 2, "modulepreload": 0},
  "has_viewport": true,
  "weight": {"css_bytes": 120000, "js_bytes": 480000, "img_bytes": 900000,
             "total_bytes": 1541234, "requests": 38},
  "third_party_origins": ["fonts.googleapis.com", ...],
  "psi": { ... } | null
}

Uses only the Python standard library.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import deque
from html.parser import HTMLParser

USER_AGENT = "CoreWebVitalsAuditBot/1.0 (+claude-skill)"
TIMEOUT = 20
SM_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
PSI_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

# Resource size cache shared across all pages so common assets are fetched once.
_SIZE_CACHE = {}


class VitalsParser(HTMLParser):
    """Extract render-blocking resources, images, hints, scripts, and DOM size."""

    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.in_head = False
        self.head_done = False
        self.dom_nodes = 0
        self.render_blocking_css = 0
        self.render_blocking_js = 0
        self.total_scripts = 0
        self.inline_script_bytes = 0
        self.inline_style_bytes = 0
        self.css_urls = []
        self.js_urls = []
        self.img_urls = []
        self.image_count = 0
        self.images_missing_dimensions = 0
        self.images_no_lazy = 0
        self.first_image_lazy = None
        self.has_viewport = False
        self.hints = {"preconnect": 0, "dns_prefetch": 0, "preload": 0, "modulepreload": 0}
        self.page_links = []
        self._in_script = False
        self._in_style = False
        self._script_is_inline = False

    def handle_starttag(self, tag, attrs):
        self.dom_nodes += 1
        a = dict(attrs)
        if tag == "head":
            self.in_head = True
        elif tag == "body":
            self.in_head = False
            self.head_done = True
        elif tag == "meta" and (a.get("name") or "").lower() == "viewport":
            self.has_viewport = True
        elif tag == "link":
            rel = (a.get("rel") or "").lower()
            href = a.get("href")
            if rel == "stylesheet" and href:
                media = (a.get("media") or "").lower()
                url = urllib.parse.urljoin(self.base_url, href.strip())
                self.css_urls.append(url)
                # Render-blocking unless explicitly print-only or preload.
                if media not in ("print",) and "preload" not in rel:
                    if not self.head_done:
                        self.render_blocking_css += 1
            elif rel == "preconnect":
                self.hints["preconnect"] += 1
            elif rel == "dns-prefetch":
                self.hints["dns_prefetch"] += 1
            elif rel == "preload":
                self.hints["preload"] += 1
            elif rel == "modulepreload":
                self.hints["modulepreload"] += 1
        elif tag == "script":
            src = a.get("src")
            is_async = "async" in a or "defer" in a
            is_module = (a.get("type") or "").lower() == "module"
            if src:
                self.total_scripts += 1
                self.js_urls.append(urllib.parse.urljoin(self.base_url, src.strip()))
                if not self.head_done and not is_async and not is_module:
                    self.render_blocking_js += 1
            else:
                self._in_script = True
                self._script_is_inline = True
        elif tag == "style":
            self._in_style = True
        elif tag == "img":
            self.image_count += 1
            has_dims = a.get("width") and a.get("height")
            if not has_dims:
                self.images_missing_dimensions += 1
            loading = (a.get("loading") or "").lower()
            if loading != "lazy":
                self.images_no_lazy += 1
            if self.first_image_lazy is None:
                self.first_image_lazy = (loading == "lazy")
            if a.get("src"):
                self.img_urls.append(urllib.parse.urljoin(self.base_url, a["src"].strip()))
        elif tag == "a" and a.get("href"):
            href = a["href"].strip()
            if not href.startswith(("mailto:", "tel:", "javascript:", "#")):
                self.page_links.append(
                    urllib.parse.urldefrag(urllib.parse.urljoin(self.base_url, href))[0])

    def handle_endtag(self, tag):
        if tag == "script" and self._in_script:
            self._in_script = False
        elif tag == "style" and self._in_style:
            self._in_style = False

    def handle_data(self, data):
        if self._in_script:
            self.inline_script_bytes += len(data.encode("utf-8"))
        elif self._in_style:
            self.inline_style_bytes += len(data.encode("utf-8"))


def norm_host(host):
    host = host.lower()
    return host[4:] if host.startswith("www.") else host


def fetch_page(url):
    """Fetch a page (follows redirects). Returns (status, final_url, body, headers, ttfb_ms, fetch_ms)."""
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, br"})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            first = resp.read(1)
            ttfb = (time.perf_counter() - t0) * 1000
            rest = resp.read(5_000_000)
            fetch_ms = (time.perf_counter() - t0) * 1000
            raw = first + rest
            return resp.status, resp.geturl(), raw, resp.headers, ttfb, fetch_ms
    except urllib.error.HTTPError as e:
        return e.code, url, b"", (e.headers if e.headers else None), None, None
    except Exception:
        return 0, url, b"", None, None, None


def resource_size(url):
    """Return (transfer_bytes, cache_control) for a subresource, cached. Uses GET with gzip."""
    if url in _SIZE_CACHE:
        return _SIZE_CACHE[url]
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, br"})
    result = (0, None)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            cl = resp.headers.get("Content-Length")
            if cl and cl.isdigit():
                size = int(cl)
            else:
                size = len(resp.read(10_000_000))
            result = (size, resp.headers.get("Cache-Control"))
    except Exception:
        result = (0, None)
    _SIZE_CACHE[url] = result
    return result


def decode_html(raw, headers):
    enc = (headers.get("Content-Encoding", "") if headers else "").lower()
    data = raw
    try:
        if "gzip" in enc:
            import gzip
            data = gzip.decompress(raw)
        elif "br" in enc:
            try:
                import brotli  # not stdlib; only if available
                data = brotli.decompress(raw)
            except Exception:
                data = raw
    except Exception:
        data = raw
    return data.decode("utf-8", errors="replace")


def has_compression(headers):
    enc = (headers.get("Content-Encoding", "") if headers else "").lower()
    return "gzip" in enc or "br" in enc or "deflate" in enc


def fetch_psi(url, strategy, key):
    params = {"url": url, "category": "performance", "strategy": strategy}
    if key:
        params["key"] = key
    q = PSI_ENDPOINT + "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(q, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}
    out = {"strategy": strategy}
    le = data.get("loadingExperience", {}).get("metrics", {})

    def field(key_name):
        m = le.get(key_name)
        if not m:
            return None
        return {"percentile": m.get("percentile"), "category": m.get("category")}

    out["field"] = {
        "LCP": field("LARGEST_CONTENTFUL_PAINT_MS"),
        "CLS": field("CUMULATIVE_LAYOUT_SHIFT_SCORE"),
        "INP": field("INTERACTION_TO_NEXT_PAINT"),
        "FCP": field("FIRST_CONTENTFUL_PAINT_MS"),
        "TTFB": field("EXPERIMENTAL_TIME_TO_FIRST_BYTE"),
    }
    lh = data.get("lighthouseResult", {})
    cats = lh.get("categories", {}).get("performance", {})
    out["lab_score"] = round(cats.get("score") * 100) if cats.get("score") is not None else None
    audits = lh.get("audits", {})

    def lab(metric):
        a = audits.get(metric, {})
        return a.get("numericValue")

    out["lab"] = {
        "LCP_ms": lab("largest-contentful-paint"),
        "CLS": lab("cumulative-layout-shift"),
        "TBT_ms": lab("total-blocking-time"),
        "FCP_ms": lab("first-contentful-paint"),
        "SI_ms": lab("speed-index"),
    }
    return out


def collect_page(url, do_psi, psi_strategy, psi_key):
    status, final_url, raw, headers, ttfb, fetch_ms = fetch_page(url)
    page = {
        "status": status, "final_url": final_url,
        "ttfb_ms": round(ttfb) if ttfb else None,
        "fetch_ms": round(fetch_ms) if fetch_ms else None,
        "html_bytes": len(raw), "html_compressed": has_compression(headers),
        "html_cache_control": headers.get("Cache-Control") if headers else None,
        "render_blocking_css": 0, "render_blocking_js": 0, "total_scripts": 0,
        "inline_script_bytes": 0, "inline_style_bytes": 0,
        "image_count": 0, "images_missing_dimensions": 0, "images_no_lazy": 0,
        "lcp_image_lazy": False, "dom_nodes": 0,
        "resource_hints": {"preconnect": 0, "dns_prefetch": 0, "preload": 0, "modulepreload": 0},
        "has_viewport": False,
        "weight": {"css_bytes": 0, "js_bytes": 0, "img_bytes": 0, "total_bytes": 0, "requests": 0},
        "third_party_origins": [], "psi": None, "_links": [],
    }
    if not raw or "html" not in (headers.get("Content-Type", "") if headers else ""):
        return page

    html = decode_html(raw, headers)
    parser = VitalsParser(final_url)
    try:
        parser.feed(html)
    except Exception:
        pass

    page.update({
        "render_blocking_css": parser.render_blocking_css,
        "render_blocking_js": parser.render_blocking_js,
        "total_scripts": parser.total_scripts,
        "inline_script_bytes": parser.inline_script_bytes,
        "inline_style_bytes": parser.inline_style_bytes,
        "image_count": parser.image_count,
        "images_missing_dimensions": parser.images_missing_dimensions,
        "images_no_lazy": parser.images_no_lazy,
        "lcp_image_lazy": bool(parser.first_image_lazy),
        "dom_nodes": parser.dom_nodes,
        "resource_hints": parser.hints,
        "has_viewport": parser.has_viewport,
        "_links": parser.page_links,
    })

    site_host = norm_host(urllib.parse.urlparse(final_url).netloc)
    third_party = set()
    css_bytes = js_bytes = img_bytes = 0
    requests = 1  # the HTML document itself
    for u in parser.css_urls:
        size, _cc = resource_size(u)
        css_bytes += size
        requests += 1
        h = norm_host(urllib.parse.urlparse(u).netloc)
        if h and h != site_host:
            third_party.add(h)
    for u in parser.js_urls:
        size, _cc = resource_size(u)
        js_bytes += size
        requests += 1
        h = norm_host(urllib.parse.urlparse(u).netloc)
        if h and h != site_host:
            third_party.add(h)
    for u in parser.img_urls:
        size, _cc = resource_size(u)
        img_bytes += size
        requests += 1
        h = norm_host(urllib.parse.urlparse(u).netloc)
        if h and h != site_host:
            third_party.add(h)

    page["weight"] = {
        "css_bytes": css_bytes, "js_bytes": js_bytes, "img_bytes": img_bytes,
        "total_bytes": page["html_bytes"] + css_bytes + js_bytes + img_bytes,
        "requests": requests,
    }
    page["third_party_origins"] = sorted(third_party)

    if do_psi:
        page["psi"] = fetch_psi(final_url, psi_strategy, psi_key)
    return page


def urls_from_sitemap(source):
    try:
        req = urllib.request.Request(source, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read(10_000_000).decode("utf-8", errors="replace")
        root = ET.fromstring(body)
    except Exception:
        return []
    if root.tag.lower().endswith("sitemapindex"):
        out = []
        for loc in root.iter(SM_NS + "loc"):
            if loc.text:
                try:
                    req = urllib.request.Request(loc.text.strip(), headers={"User-Agent": USER_AGENT})
                    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                        sub = ET.fromstring(resp.read(10_000_000).decode("utf-8", errors="replace"))
                    out += [l.text.strip() for l in sub.iter(SM_NS + "loc") if l.text]
                except Exception:
                    continue
        return out
    return [loc.text.strip() for loc in root.iter(SM_NS + "loc") if loc.text]


def main():
    ap = argparse.ArgumentParser(description="Collect Core Web Vitals signals for a site.")
    ap.add_argument("source", help="Site root URL, sitemap (--sitemap), or URL list file (--url-list)")
    ap.add_argument("--max-pages", type=int, default=50,
                    help="max pages to analyze (default 50; CWV collection is heavier than a text crawl)")
    ap.add_argument("--output", default="vitals_inventory.json")
    ap.add_argument("--sitemap", action="store_true")
    ap.add_argument("--url-list", action="store_true")
    ap.add_argument("--psi", action="store_true", help="also fetch Google PageSpeed Insights data")
    ap.add_argument("--psi-strategy", choices=["mobile", "desktop"], default="mobile")
    ap.add_argument("--psi-key", default=None, help="PageSpeed Insights API key (raises rate limits)")
    args = ap.parse_args()

    crawl_mode = not args.url_list and not args.sitemap
    if args.url_list:
        with open(args.source, encoding="utf-8") as f:
            seeds = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    elif args.sitemap:
        seeds = urls_from_sitemap(args.source)
    else:
        seeds = [args.source.rstrip("/")]

    host = norm_host(urllib.parse.urlparse(seeds[0]).netloc) if seeds else ""
    pages = {}
    queue = deque(seeds)
    seen = set(seeds)

    while queue and len(pages) < args.max_pages:
        url = queue.popleft()
        page = collect_page(url, args.psi, args.psi_strategy, args.psi_key)
        links = page.pop("_links", [])
        pages[url] = page
        w = page["weight"]
        print(f"[{page['status']}] {w['total_bytes']//1024}KB {w['requests']} req  "
              f"blockCSS={page['render_blocking_css']} blockJS={page['render_blocking_js']}  {url}",
              file=sys.stderr)
        if crawl_mode:
            for link in links:
                if norm_host(urllib.parse.urlparse(link).netloc) == host and link not in seen \
                        and len(seen) < args.max_pages:
                    seen.add(link)
                    queue.append(link)

    out = {"site": args.source, "psi_enabled": args.psi,
           "psi_strategy": args.psi_strategy if args.psi else None, "pages": pages}
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(pages)} pages to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
