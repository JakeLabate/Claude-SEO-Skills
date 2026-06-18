#!/usr/bin/env python3
"""Fetch and parse a site's /llms.txt, then probe every link it references into a JSON inventory.

Usage:
    python3 collect_llms.py https://example.com [--max-urls 300] [--output llms_inventory.json]
    python3 collect_llms.py https://example.com/llms.txt --llms [--output llms_inventory.json]

The llms.txt proposal (https://llmstxt.org) defines a markdown file at /llms.txt:
an H1 project name (required), an optional blockquote summary, optional free
markdown, then H2 sections whose list items are links of the form
"- [name](url): optional notes". This script fetches /llms.txt without
auto-following redirects, records status / content type / size, parses that
structure, and probes every linked URL (status, redirect target, canonical, meta
robots, X-Robots-Tag, robots.txt disallow). It also checks whether /llms-full.txt
exists.

Output JSON schema:
{
  "site": "https://example.com",
  "llms_url": "https://example.com/llms.txt",
  "fetch": {"found": true, "status": 200, "content_type": "text/markdown",
            "bytes": 1234, "redirected": false, "final_url": "...",
            "looks_like_html": false},
  "raw": "<full llms.txt text>",
  "h1": "Project Name|null",
  "summary": "blockquote text|null",
  "sections": [{"heading": "Docs", "optional": false,
                "items": [{"raw": "...", "is_link": true, "title": "...",
                           "url": "...", "description": "...", "relative": false}]}],
  "links": {"<url>": {"sections": ["Docs"], "status": 200, "redirected": false,
                      "final_url": "...", "canonical": "...|null",
                      "meta_robots": "...|null", "x_robots_tag": "...|null",
                      "robots_disallowed": false}},
  "llms_full_txt": {"checked": "https://…/llms-full.txt", "status": 200, "found": true}
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
from html.parser import HTMLParser

USER_AGENT = "LlmsTxtAuditBot/1.0 (+claude-skill)"
TIMEOUT = 15
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


class PageHeadParser(HTMLParser):
    """Extract canonical and meta robots only."""

    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.canonical = None
        self.meta_robots = None
        self._body_started = False

    def handle_starttag(self, tag, attrs):
        if tag == "body":
            self._body_started = True
        if self._body_started:
            return
        a = dict(attrs)
        if tag == "link" and (a.get("rel") or "").lower() == "canonical" and a.get("href"):
            self.canonical = urllib.parse.urljoin(self.base_url, a["href"].strip())
        elif tag == "meta" and (a.get("name") or "").lower() == "robots":
            self.meta_robots = a.get("content")


def norm_host(host):
    host = host.lower()
    return host[4:] if host.startswith("www.") else host


def raw_get(url, max_bytes=3_000_000):
    """Plain GET (auto-follows redirects). Returns (status, final_url, raw_bytes, headers)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, resp.geturl(), resp.read(max_bytes), resp.headers
    except urllib.error.HTTPError as e:
        return e.code, url, b"", (e.headers if e.headers else None)
    except Exception:
        return 0, url, b"", None


def fetch_no_follow(url):
    """Fetch without following redirects. Returns (status, location, body_text_or_none, headers)."""

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with opener.open(req, timeout=TIMEOUT) as resp:
            ctype = resp.headers.get("Content-Type", "")
            body = resp.read(2_000_000).decode("utf-8", errors="replace") if "html" in ctype else None
            return resp.status, None, body, resp.headers
    except urllib.error.HTTPError as e:
        loc = e.headers.get("Location") if e.headers else None
        return e.code, loc, None, (e.headers if e.headers else None)
    except Exception:
        return 0, None, None, None


def fetch_text_no_follow(url):
    """Fetch a text file without following redirects. Returns (status, location, text, headers)."""

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with opener.open(req, timeout=TIMEOUT) as resp:
            return resp.status, None, resp.read(2_000_000).decode("utf-8", errors="replace"), resp.headers
    except urllib.error.HTTPError as e:
        loc = e.headers.get("Location") if e.headers else None
        return e.code, loc, "", (e.headers if e.headers else None)
    except Exception:
        return 0, None, "", None


def parse_robots_disallow(site_root):
    """Fetch robots.txt and return the list of Disallow paths for User-agent: *."""
    status, _f, raw, _h = raw_get(site_root.rstrip("/") + "/robots.txt", max_bytes=1_000_000)
    if status != 200:
        return []
    text = raw.decode("utf-8", errors="replace")
    disallow, in_star, after_directive = [], False, False
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, _, value = line.partition(":")
        field, value = field.strip().lower(), value.strip()
        if field == "user-agent":
            # A new group starts after the previous group's directives ended.
            if after_directive:
                in_star = False
            in_star = in_star or (value == "*")
            after_directive = False
        elif field == "disallow":
            after_directive = True
            if in_star and value:
                disallow.append(value)
        elif field == "allow":
            after_directive = True
    return disallow


def robots_disallowed(path, disallow):
    return any(path.startswith(rule) for rule in disallow)


def parse_llms(text):
    """Parse llms.txt markdown into h1, summary blockquote, and H2 sections of list items."""
    h1 = None
    summary = None
    sections = []
    current = None
    seen_h1 = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("##"):
            if h1 is None:
                h1 = stripped[2:].strip()
            seen_h1 = True
            continue
        if stripped.startswith("## "):
            heading = stripped[3:].strip()
            current = {"heading": heading, "optional": heading.lower() == "optional", "items": []}
            sections.append(current)
            continue
        if summary is None and seen_h1 and current is None and stripped.startswith(">"):
            summary = stripped.lstrip(">").strip()
            continue
        if current is not None and re.match(r"^[-*+]\s+", stripped):
            item_text = re.sub(r"^[-*+]\s+", "", stripped)
            m = LINK_RE.search(item_text)
            if m:
                title, url = m.group(1).strip(), m.group(2).strip()
                # Description is whatever follows the link, after an optional ": ".
                tail = item_text[m.end():].lstrip()
                if tail.startswith(":"):
                    tail = tail[1:].strip()
                relative = not bool(urllib.parse.urlparse(url).scheme) and not url.startswith("//")
                current["items"].append({
                    "raw": item_text, "is_link": True, "title": title, "url": url,
                    "description": tail or None, "relative": relative,
                })
            else:
                current["items"].append({
                    "raw": item_text, "is_link": False, "title": None, "url": None,
                    "description": None, "relative": False,
                })
    return h1, summary, sections


def probe_url(loc, disallow):
    status, location, body, headers = fetch_no_follow(loc)
    redirected = 300 <= status < 400
    final_url = urllib.parse.urljoin(loc, location) if (redirected and location) else loc
    x_robots = headers.get("X-Robots-Tag") if headers else None
    canonical = meta_robots = None
    if body:
        parser = PageHeadParser(loc)
        try:
            parser.feed(body)
        except Exception:
            pass
        canonical, meta_robots = parser.canonical, parser.meta_robots
    path = urllib.parse.urlparse(loc).path or "/"
    return {
        "status": status, "redirected": redirected, "final_url": final_url,
        "canonical": canonical, "meta_robots": meta_robots, "x_robots_tag": x_robots,
        "robots_disallowed": robots_disallowed(path, disallow),
    }


def main():
    ap = argparse.ArgumentParser(description="Fetch, parse, and probe a site's llms.txt.")
    ap.add_argument("source", help="Site root URL, or an llms.txt URL with --llms")
    ap.add_argument("--llms", action="store_true", help="Treat source as an llms.txt URL directly")
    ap.add_argument("--max-urls", type=int, default=300, help="max linked URLs to probe (default 300)")
    ap.add_argument("--no-probe", action="store_true", help="parse but skip per-link probing")
    ap.add_argument("--output", default="llms_inventory.json")
    args = ap.parse_args()

    if args.llms:
        pu = urllib.parse.urlparse(args.source)
        site_root = f"{pu.scheme}://{pu.netloc}"
        llms_url = args.source
    else:
        site_root = args.source.rstrip("/")
        llms_url = site_root + "/llms.txt"

    status, location, text, headers = fetch_text_no_follow(llms_url)
    redirected = 300 <= status < 400
    final_url = urllib.parse.urljoin(llms_url, location) if (redirected and location) else llms_url
    content_type = (headers.get("Content-Type", "") if headers else "") or ""
    if redirected and location:
        # Follow the redirect once so a moved file is still parsed.
        _st, _l, text, _h = fetch_text_no_follow(final_url)
    text = text or ""
    looks_like_html = "<html" in text[:2000].lower() or "<!doctype html" in text[:2000].lower()

    fetch = {
        "found": status == 200, "status": status, "content_type": content_type,
        "bytes": len(text.encode("utf-8")), "redirected": redirected,
        "final_url": final_url, "looks_like_html": looks_like_html,
    }
    print(f"llms.txt: [{status}] {llms_url} ({fetch['bytes']} bytes)", file=sys.stderr)

    h1 = summary = None
    sections = []
    if status == 200 and not looks_like_html:
        h1, summary, sections = parse_llms(text)

    # Gather links (absolute-resolved) and which sections they appear in.
    disallow = parse_robots_disallow(site_root)
    link_sections = {}
    for sec in sections:
        for item in sec["items"]:
            if item["is_link"] and item["url"]:
                resolved = urllib.parse.urljoin(llms_url, item["url"])
                link_sections.setdefault(resolved, []).append(sec["heading"])

    links = {}
    locs = list(link_sections.keys())[: args.max_urls]
    for i, loc in enumerate(locs, 1):
        entry = {"sections": link_sections[loc]}
        if not args.no_probe:
            entry.update(probe_url(loc, disallow))
            print(f"  [{entry.get('status')}] ({i}/{len(locs)}) {loc}", file=sys.stderr)
        links[loc] = entry

    # Check llms-full.txt.
    full_url = site_root + "/llms-full.txt"
    fst, _fl, _ft, _fh = fetch_text_no_follow(full_url)
    llms_full = {"checked": full_url, "status": fst, "found": fst == 200}

    out = {
        "site": site_root,
        "llms_url": llms_url,
        "fetch": fetch,
        "raw": text,
        "h1": h1,
        "summary": summary,
        "sections": sections,
        "links": links,
        "llms_full_txt": llms_full,
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(sections)} sections, {len(link_sections)} links "
          f"({len(links)} probed) to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
