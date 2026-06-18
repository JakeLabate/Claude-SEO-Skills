#!/usr/bin/env python3
"""Audit a redirect inventory JSON (from collect_redirects.py) and emit findings.

Usage:
    python3 audit_redirects.py redirect_inventory.json [--output audit_report.json] [--max-chain 1]

Checks implemented (see references/audit-checks.md):
- redirect_loop: the chain returns to a URL already visited (high)
- redirect_to_error: the chain ends on a 4xx/5xx/0 status (high)
- exceeded_max_hops: chain longer than the resolver limit; likely a loop (high)
- chain_too_long: more redirect hops than --max-chain (high)
- temporary_redirect: 302/303/307 used where a permanent move is implied (medium)
- meta_or_js_redirect: client-side meta-refresh or JS redirect instead of a 301 (medium)
- mixed_redirect_types: a single chain mixes permanent and temporary codes (medium)
- downgrade_to_http: a hop redirects from HTTPS to HTTP (high)
- drops_query: redirect target silently drops the query string (low)
- canonical_to_redirect: a 200 page's canonical points at a URL that itself redirects (medium)
- redirecting_canonical_target: the final page's canonical differs from its own final URL (low)

Uses only the Python standard library.
"""

import argparse
import json
import sys
import urllib.parse

PERMANENT = {301, 308}
TEMPORARY = {302, 303, 307}


def norm(url):
    return urllib.parse.urldefrag((url or "").strip())[0].rstrip("/").lower()


def main():
    ap = argparse.ArgumentParser(description="Run redirect audit checks.")
    ap.add_argument("inventory", help="redirect_inventory.json from collect_redirects.py")
    ap.add_argument("--output", default="audit_report.json")
    ap.add_argument("--max-chain", type=int, default=1,
                    help="max acceptable redirect hops before flagging chain_too_long (default 1)")
    args = ap.parse_args()

    with open(args.inventory, encoding="utf-8") as f:
        data = json.load(f)
    pages = data.get("pages", {})

    findings = {
        "redirect_loop": [], "redirect_to_error": [], "exceeded_max_hops": [],
        "chain_too_long": [], "temporary_redirect": [], "meta_or_js_redirect": [],
        "mixed_redirect_types": [], "downgrade_to_http": [], "drops_query": [],
        "canonical_to_redirect": [], "redirecting_canonical_target": [],
    }

    # Map every requested URL to its final status so canonical-to-redirect can be checked.
    final_status_by_url = {norm(u): p.get("final_status") for u, p in pages.items()}
    redirecting_urls = {norm(u) for u, p in pages.items() if p.get("chain_length", 0) > 0}

    hop_count = {"0": 0, "1": 0, "2": 0, "3+": 0}

    for url, p in pages.items():
        chain = p.get("chain_length", 0)
        if chain == 0:
            hop_count["0"] += 1
        elif chain == 1:
            hop_count["1"] += 1
        elif chain == 2:
            hop_count["2"] += 1
        else:
            hop_count["3+"] += 1

        codes = set(p.get("status_codes", []))
        final = p.get("final_status")

        if p.get("loop"):
            findings["redirect_loop"].append({"page": url, "hops": p.get("hops", [])})
        if p.get("exceeded_max_hops"):
            findings["exceeded_max_hops"].append({"page": url, "chain_length": chain})

        if chain > 0 and (final == 0 or (final and final >= 400)):
            findings["redirect_to_error"].append(
                {"page": url, "final_url": p.get("final_url"), "final_status": final})

        if chain > args.max_chain:
            findings["chain_too_long"].append(
                {"page": url, "chain_length": chain, "final_url": p.get("final_url"),
                 "hops": [h["status"] for h in p.get("hops", [])]})

        if codes & TEMPORARY:
            findings["temporary_redirect"].append(
                {"page": url, "codes": sorted(codes), "final_url": p.get("final_url")})

        if (codes & PERMANENT) and (codes & TEMPORARY):
            findings["mixed_redirect_types"].append(
                {"page": url, "codes": sorted(codes), "final_url": p.get("final_url")})

        if p.get("downgrade_to_http"):
            findings["downgrade_to_http"].append({"page": url, "hops": p.get("hops", [])})

        if p.get("drops_query"):
            findings["drops_query"].append(
                {"page": url, "final_url": p.get("final_url")})

        mr = p.get("meta_refresh", {}) or {}
        if mr.get("found") or p.get("js_redirect"):
            findings["meta_or_js_redirect"].append({
                "page": url,
                "type": "meta-refresh" if mr.get("found") else "javascript",
                "target": mr.get("url"),
            })

        # Canonical pointing at a URL that itself redirects (only meaningful on 200 finals).
        canonical = p.get("final_canonical")
        if final == 200 and canonical:
            c = norm(canonical)
            if c in redirecting_urls and c != norm(p.get("final_url", "")):
                findings["canonical_to_redirect"].append(
                    {"page": url, "canonical": canonical, "canonical_final_status": final_status_by_url.get(c)})
            elif c != norm(p.get("final_url", "")) and c not in final_status_by_url:
                findings["redirecting_canonical_target"].append(
                    {"page": p.get("final_url"), "canonical": canonical})

    severity = {
        "redirect_loop": "high", "redirect_to_error": "high", "exceeded_max_hops": "high",
        "chain_too_long": "high", "downgrade_to_http": "high",
        "temporary_redirect": "medium", "meta_or_js_redirect": "medium",
        "mixed_redirect_types": "medium", "canonical_to_redirect": "medium",
        "drops_query": "low", "redirecting_canonical_target": "low",
    }
    summary = {
        "urls_checked": len(pages),
        "urls_redirecting": sum(1 for p in pages.values() if p.get("chain_length", 0) > 0),
        "hop_distribution": hop_count,
        "issues_by_check": {k: len(v) for k, v in findings.items()},
        "issues_by_severity": {
            level: sum(len(findings[k]) for k, s in severity.items() if s == level)
            for level in ("high", "medium", "low")
        },
    }
    report = {"summary": summary, "severity": severity, "findings": findings}

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(json.dumps(summary, indent=2))
    print(f"Full report written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
