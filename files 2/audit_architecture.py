#!/usr/bin/env python3
"""Analyze an architecture inventory JSON (from crawl_architecture.py) and emit audit findings.

Usage:
    python3 audit_architecture.py architecture_inventory.json [--output audit_report.json]
        [--max-url-depth 4] [--max-click-depth 3] [--tracking-params utm_source,gclid,fbclid]

Checks implemented (see references/audit-checks.md):
- multiple_host_variants: more than one 200 host/protocol variant (high)
- robots_blocks_content: Disallow rules matching linked/indexable pages (high)
- directive_conflicts: disallow+noindex, noindex+canonical-elsewhere, canonical to bad target (high)
- sitemap_non_indexable: sitemap URLs that are non-200/redirect/noindex/non-canonical (high)
- sitemap_missing_pages: indexable pages absent from the sitemap (medium)
- deep_pages / depth_distribution: click depth issues (medium)
- url_quality: uppercase/underscore/space/over-long/over-deep/id-only URLs (medium)
- inconsistent_url_forms: mixed trailing slash, http/https, www in internal links (medium)
- parameter_urls: tracking/session/sort params in internal links (medium)
- missing_robots / missing_sitemap (medium)
- missing_self_canonical (low)
- sitemap_not_in_robots (low)
- thin_directories (low)
- sitemap_over_limit (low)

Uses only the Python standard library.
"""

import argparse
import json
import re
import sys
import urllib.parse
from collections import Counter, defaultdict

SITEMAP_URL_LIMIT = 50000
TRACKING_DEFAULT = ["utm_source", "utm_medium", "utm_campaign", "utm_term",
                    "utm_content", "gclid", "fbclid", "mc_cid", "mc_eid"]
SESSION_PARAMS = ["sid", "sessionid", "phpsessid", "jsessionid", "aspsessionid"]
ID_SLUG = re.compile(r"^(\d+|[0-9a-f]{12,}|[0-9a-f-]{20,})$", re.I)


def norm_host(host):
    host = host.lower()
    return host[4:] if host.startswith("www.") else host


def normalize_url(url):
    """Canonical comparison key: lowercase host, strip default ports and fragment, keep path/query."""
    p = urllib.parse.urlparse(url)
    netloc = p.netloc.lower()
    netloc = re.sub(r":(80|443)$", "", netloc)
    path = p.path or "/"
    return urllib.parse.urlunparse((p.scheme, netloc, path, "", p.query, ""))


def strip_slash(url):
    p = urllib.parse.urlparse(url)
    path = p.path.rstrip("/") or "/"
    return urllib.parse.urlunparse((p.scheme, p.netloc.lower(), path, "", p.query, ""))


def robots_match(path, rules, agent="*"):
    """Return True if path is Disallowed for the given agent (longest-match, Allow wins on ties)."""
    applicable = [r for r in rules if r["agent"] == agent]
    if not applicable:
        applicable = [r for r in rules if r["agent"] == "*"]
    if not applicable:
        return False
    disallow, allow = [], []
    for r in applicable:
        disallow.extend(r["disallow"])
        allow.extend(r["allow"])

    def pattern_len(pattern):
        if pattern == "":
            return None  # empty Disallow means allow everything
        regex = re.escape(pattern).replace(r"\*", ".*")
        if regex.endswith(r"\$"):
            regex = regex[:-2] + "$"
        m = re.match(regex, path)
        return len(pattern) if m else -1

    best_dis = max([pattern_len(p) for p in disallow if pattern_len(p) is not None] or [-1])
    best_allow = max([pattern_len(p) for p in allow if pattern_len(p) is not None] or [-1])
    if best_dis < 0:
        return False
    return best_dis > best_allow


def is_noindex(meta_robots):
    return "noindex" in (meta_robots or "").lower()


def main():
    ap = argparse.ArgumentParser(description="Run architecture audit checks on an inventory.")
    ap.add_argument("inventory")
    ap.add_argument("--output", default="audit_report.json")
    ap.add_argument("--max-url-depth", type=int, default=4)
    ap.add_argument("--max-click-depth", type=int, default=3)
    ap.add_argument("--tracking-params", default="")
    args = ap.parse_args()

    with open(args.inventory, encoding="utf-8") as f:
        inv = json.load(f)

    pages = inv["pages"]
    host_variants = inv.get("host_variants", {})
    robots = inv.get("robots_txt", {})
    sitemap = inv.get("sitemap", {})
    rules = robots.get("rules", [])
    tracking = set(TRACKING_DEFAULT + [t.strip() for t in args.tracking_params.split(",") if t.strip()])

    findings = {
        "multiple_host_variants": [], "robots_blocks_content": [], "directive_conflicts": [],
        "sitemap_non_indexable": [], "sitemap_missing_pages": [],
        "deep_pages": [], "url_quality": [], "inconsistent_url_forms": [],
        "parameter_urls": [], "missing_robots": [], "missing_sitemap": [],
        "missing_self_canonical": [], "sitemap_not_in_robots": [],
        "thin_directories": [], "sitemap_over_limit": [],
    }

    # --- 1. Host/protocol variants -------------------------------------------------
    live_200 = [v for v, info in host_variants.items() if info.get("status") == 200]
    if len(live_200) > 1:
        findings["multiple_host_variants"].append({
            "variants_200": live_200,
            "canonical_host": inv.get("canonical_host"),
            "detail": "More than one host/protocol variant returns 200; redirect all but the canonical host.",
        })

    # --- robots.txt / sitemap presence --------------------------------------------
    if not robots.get("found"):
        findings["missing_robots"].append(
            {"status": robots.get("status"),
             "detail": "robots.txt missing or non-200; serve a valid robots.txt and declare the sitemap."})
    if not sitemap.get("found"):
        findings["missing_sitemap"].append(
            {"detail": "No XML sitemap found at /sitemap.xml or via robots.txt."})
    elif not robots.get("sitemaps"):
        findings["sitemap_not_in_robots"].append(
            {"detail": "A sitemap exists but is not referenced with a Sitemap: line in robots.txt."})

    if sitemap.get("url_count", 0) > SITEMAP_URL_LIMIT and len(sitemap.get("sources", [])) <= 1:
        findings["sitemap_over_limit"].append(
            {"url_count": sitemap["url_count"],
             "detail": f"Single sitemap has {sitemap['url_count']} URLs (limit {SITEMAP_URL_LIMIT}); split with a sitemap index."})

    # --- Build lookups for indexability -------------------------------------------
    # A crawled page is "indexable" if 200, not noindex, and self-canonical (or no canonical).
    indexable_keys = {}     # normalized self-URL -> requested url
    page_by_norm = {}       # normalized requested url -> page
    canonical_target = {}   # normalized requested url -> normalized canonical
    status_by_norm = {}
    noindex_by_norm = {}
    redirected_by_norm = {}

    for url, page in pages.items():
        nkey = normalize_url(url)
        page_by_norm[nkey] = page
        status_by_norm[nkey] = page["status"]
        noindex_by_norm[nkey] = is_noindex(page.get("meta_robots"))
        redirected_by_norm[nkey] = page.get("redirected", False)
        canon = page.get("canonical")
        if canon:
            canonical_target[nkey] = normalize_url(canon)
        self_canon = (not canon) or strip_slash(canon) == strip_slash(url)
        if page["status"] == 200 and not noindex_by_norm[nkey] and self_canon:
            indexable_keys[nkey] = url

    # --- 2. robots.txt blocks indexable/linked content ----------------------------
    for nkey, url in indexable_keys.items():
        path = urllib.parse.urlparse(url).path or "/"
        if robots_match(path, rules):
            findings["robots_blocks_content"].append(
                {"page": url, "detail": "Disallowed in robots.txt but linked and otherwise indexable."})

    # --- 3. Directive conflicts ----------------------------------------------------
    for url, page in pages.items():
        nkey = normalize_url(url)
        path = urllib.parse.urlparse(url).path or "/"
        noidx = noindex_by_norm[nkey]
        canon = page.get("canonical")

        if noidx and robots_match(path, rules):
            findings["directive_conflicts"].append(
                {"page": url, "conflict": "disallow + noindex",
                 "detail": "Page is Disallowed in robots.txt, so the noindex can never be seen."})

        if noidx and canon and strip_slash(canon) != strip_slash(url):
            findings["directive_conflicts"].append(
                {"page": url, "conflict": "noindex + canonical elsewhere",
                 "detail": f"noindex contradicts canonical -> {canon}."})

        if canon:
            ckey = normalize_url(canon)
            if ckey in status_by_norm:
                if status_by_norm[ckey] >= 400 or status_by_norm[ckey] == 0:
                    findings["directive_conflicts"].append(
                        {"page": url, "conflict": "canonical to broken URL",
                         "detail": f"canonical -> {canon} returns {status_by_norm[ckey]}."})
                elif redirected_by_norm.get(ckey):
                    findings["directive_conflicts"].append(
                        {"page": url, "conflict": "canonical to redirect",
                         "detail": f"canonical -> {canon} is itself a redirect."})
                elif noindex_by_norm.get(ckey) and ckey != nkey:
                    findings["directive_conflicts"].append(
                        {"page": url, "conflict": "canonical to noindex",
                         "detail": f"canonical -> {canon} is noindex."})

    # --- 4 & 5. Sitemap parity -----------------------------------------------------
    sitemap_urls = sitemap.get("urls", [])
    sitemap_norm = {normalize_url(u): u for u in sitemap_urls}
    for nkey, original in sitemap_norm.items():
        page = page_by_norm.get(nkey)
        if page is None:
            continue  # not crawled; cannot assess
        problem = None
        if page["status"] >= 400 or page["status"] == 0:
            problem = f"returns {page['status']}"
        elif page.get("redirected"):
            problem = f"redirects to {page.get('final_url')}"
        elif is_noindex(page.get("meta_robots")):
            problem = "is noindex"
        else:
            canon = page.get("canonical")
            if canon and strip_slash(canon) != strip_slash(original):
                problem = f"canonical points to {canon}"
        if problem:
            findings["sitemap_non_indexable"].append({"sitemap_url": original, "problem": problem})

    sitemap_slash_set = {strip_slash(u) for u in sitemap_urls}
    if sitemap.get("found"):
        for nkey, url in indexable_keys.items():
            if strip_slash(url) not in sitemap_slash_set:
                findings["sitemap_missing_pages"].append({"page": url})

    # --- 6. Click depth ------------------------------------------------------------
    depth_hist = Counter()
    beyond = 0
    total = 0
    for url, page in pages.items():
        if page["status"] != 200:
            continue
        total += 1
        d = page["depth"]
        depth_hist[d] += 1
        if d > args.max_click_depth:
            beyond += 1
            findings["deep_pages"].append({"page": url, "depth": d})
    depth_distribution = {
        "histogram": dict(sorted(depth_hist.items())),
        "beyond_threshold": beyond,
        "share_beyond_threshold": round(beyond / total, 3) if total else 0,
        "threshold": args.max_click_depth,
    }

    # --- 7. URL quality ------------------------------------------------------------
    for url, page in pages.items():
        if page["status"] >= 400 or page["status"] == 0:
            continue
        p = urllib.parse.urlparse(url)
        path = p.path or "/"
        problems = []
        if re.search(r"[A-Z]", path):
            problems.append("uppercase")
        if "_" in path:
            problems.append("underscore")
        if "%20" in url or " " in path or re.search(r"%[0-9A-Fa-f]{2}", path):
            problems.append("space/encoded char")
        if len(url) > 115:
            problems.append(f"long ({len(url)} chars)")
        if page["segments"] > args.max_url_depth:
            problems.append(f"deep path ({page['segments']} segments)")
        last_seg = [s for s in path.split("/") if s]
        if last_seg and ID_SLUG.match(last_seg[-1]):
            problems.append("ID-only slug")
        if problems:
            findings["url_quality"].append({"page": url, "problems": problems})

    # --- 8. Inconsistent URL forms (across internal links) ------------------------
    link_forms = []
    for page in pages.values():
        link_forms.extend(page.get("links", []))
    slash_paths = defaultdict(set)  # path without slash -> set of "slash"/"noslash"
    schemes = set()
    www_forms = set()
    for target in link_forms:
        tp = urllib.parse.urlparse(target)
        schemes.add(tp.scheme)
        www_forms.add(tp.netloc.lower().startswith("www."))
        base = tp.path.rstrip("/")
        if tp.path.endswith("/") and tp.path != "/":
            slash_paths[base].add("slash")
        elif tp.path and tp.path != "/":
            slash_paths[base].add("noslash")
    mixed_slash = [b for b, forms in slash_paths.items() if len(forms) > 1]
    if mixed_slash:
        findings["inconsistent_url_forms"].append(
            {"type": "mixed trailing slash", "examples": mixed_slash[:10],
             "count": len(mixed_slash)})
    if "http" in schemes and "https" in schemes:
        findings["inconsistent_url_forms"].append(
            {"type": "mixed http/https in internal links"})
    if len(www_forms) > 1:
        findings["inconsistent_url_forms"].append(
            {"type": "mixed www / non-www in internal links"})

    # --- 9. Parameter URLs ---------------------------------------------------------
    seen_param = set()
    for target in link_forms:
        tp = urllib.parse.urlparse(target)
        if not tp.query:
            continue
        keys = {k.lower() for k, _ in urllib.parse.parse_qsl(tp.query)}
        cat = None
        if keys & tracking:
            cat = "tracking parameter in internal link"
        elif keys & set(SESSION_PARAMS):
            cat = "session id in URL"
        else:
            cat = "functional parameter (sort/filter/pagination)"
        key = (cat, urllib.parse.urlunparse(tp._replace(query="")), tuple(sorted(keys)))
        if key in seen_param:
            continue
        seen_param.add(key)
        findings["parameter_urls"].append(
            {"url": target, "category": cat, "params": sorted(keys)})

    # --- 12. Missing self-canonical ------------------------------------------------
    for url, page in pages.items():
        if page["status"] == 200 and not is_noindex(page.get("meta_robots")) and not page.get("canonical"):
            findings["missing_self_canonical"].append({"page": url})

    # --- 14. Directory taxonomy ----------------------------------------------------
    section_counts = Counter()
    for url, page in pages.items():
        if page["status"] != 200:
            continue
        segs = [s for s in urllib.parse.urlparse(url).path.split("/") if s]
        section = "/" + segs[0] if segs else "/"
        section_counts[section] += 1
    thin = [{"section": s, "pages": c} for s, c in section_counts.items()
            if c == 1 and s != "/"]
    if thin:
        findings["thin_directories"] = thin

    severity = {
        "multiple_host_variants": "high", "robots_blocks_content": "high",
        "directive_conflicts": "high", "sitemap_non_indexable": "high",
        "sitemap_missing_pages": "medium", "deep_pages": "medium",
        "url_quality": "medium", "inconsistent_url_forms": "medium",
        "parameter_urls": "medium", "missing_robots": "medium", "missing_sitemap": "medium",
        "missing_self_canonical": "low", "sitemap_not_in_robots": "low",
        "thin_directories": "low", "sitemap_over_limit": "low",
    }

    summary = {
        "pages_crawled": inv.get("pages_crawled"),
        "canonical_host": inv.get("canonical_host"),
        "robots_found": robots.get("found"),
        "sitemap_found": sitemap.get("found"),
        "sitemap_url_count": sitemap.get("url_count"),
        "depth_distribution": depth_distribution,
        "section_counts": dict(section_counts.most_common()),
        "issues_by_check": {k: len(v) for k, v in findings.items()},
        "issues_by_severity": {
            level: sum(len(findings[k]) for k, s in severity.items() if s == level)
            for level in ("high", "medium", "low")
        },
    }
    report = {"summary": summary, "severity": severity, "findings": findings,
              "host_variants": host_variants}

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(json.dumps(summary, indent=2))
    print(f"Full report written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
