#!/usr/bin/env python3
"""Audit a vitals inventory JSON (from collect_vitals.py) and emit findings.

Usage:
    python3 audit_vitals.py vitals_inventory.json [--output audit_report.json]
        [--weight-budget 2500000] [--ttfb-budget 800]

Checks implemented (see references/audit-checks.md). When PSI field data is present
it takes precedence as the authoritative Core Web Vitals signal; the lab proxies
are reported alongside as the cause-level diagnosis.

PSI field (real CrUX), when --psi was used at collection time:
- psi_poor_lcp / psi_poor_cls / psi_poor_inp: metric category SLOW (high) or AVERAGE (medium)
- psi_low_score: Lighthouse performance score < 50 (high) or < 90 (medium)

Lab proxies (always):
- no_text_compression (high), lcp_image_lazy (high), slow_ttfb (high/medium),
  page_weight_over_budget (medium), render_blocking_js (medium), render_blocking_css (medium),
  images_missing_dimensions (medium, CLS), excessive_dom (high/medium), too_many_requests (medium),
  large_js (medium), missing_viewport (medium), missing_preconnect (low),
  large_css (low), no_lazy_loading (low)

Uses only the Python standard library.
"""

import argparse
import json
import sys


def main():
    ap = argparse.ArgumentParser(description="Run Core Web Vitals audit checks.")
    ap.add_argument("inventory", help="vitals_inventory.json from collect_vitals.py")
    ap.add_argument("--output", default="audit_report.json")
    ap.add_argument("--weight-budget", type=int, default=2_500_000,
                    help="total page transfer budget in bytes (default 2.5MB)")
    ap.add_argument("--ttfb-budget", type=int, default=800,
                    help="TTFB budget in ms (default 800; Google 'good' threshold)")
    ap.add_argument("--js-budget", type=int, default=1_000_000, help="JS transfer budget in bytes")
    ap.add_argument("--css-budget", type=int, default=150_000, help="CSS transfer budget in bytes")
    ap.add_argument("--dom-budget", type=int, default=1500, help="DOM node soft limit")
    args = ap.parse_args()

    with open(args.inventory, encoding="utf-8") as f:
        data = json.load(f)
    pages = data.get("pages", {})

    findings = {
        "psi_poor_lcp": [], "psi_poor_cls": [], "psi_poor_inp": [], "psi_low_score": [],
        "no_text_compression": [], "lcp_image_lazy": [], "slow_ttfb": [],
        "page_weight_over_budget": [], "render_blocking_js": [], "render_blocking_css": [],
        "images_missing_dimensions": [], "excessive_dom": [], "too_many_requests": [],
        "large_js": [], "missing_viewport": [], "missing_preconnect": [],
        "large_css": [], "no_lazy_loading": [],
    }

    weights = []
    for url, p in pages.items():
        if p.get("status") != 200:
            continue
        w = p.get("weight", {})
        weights.append(w.get("total_bytes", 0))

        # --- PSI field data (authoritative) ---
        psi = p.get("psi") or {}
        field = (psi.get("field") or {}) if isinstance(psi, dict) else {}
        for metric, check in (("LCP", "psi_poor_lcp"), ("CLS", "psi_poor_cls"), ("INP", "psi_poor_inp")):
            m = field.get(metric)
            if m and m.get("category") in ("SLOW", "AVERAGE"):
                findings[check].append(
                    {"page": url, "category": m.get("category"), "percentile": m.get("percentile")})
        score = psi.get("lab_score") if isinstance(psi, dict) else None
        if score is not None and score < 90:
            findings["psi_low_score"].append({"page": url, "score": score})

        # --- Lab proxies ---
        if not p.get("html_compressed") and p.get("html_bytes", 0) > 5000:
            findings["no_text_compression"].append({"page": url, "html_bytes": p.get("html_bytes")})

        if p.get("lcp_image_lazy"):
            findings["lcp_image_lazy"].append({"page": url})

        ttfb = p.get("ttfb_ms")
        if ttfb is not None and ttfb > args.ttfb_budget:
            findings["slow_ttfb"].append({"page": url, "ttfb_ms": ttfb})

        total = w.get("total_bytes", 0)
        if total > args.weight_budget:
            findings["page_weight_over_budget"].append(
                {"page": url, "total_bytes": total, "breakdown": w})

        if p.get("render_blocking_js", 0) > 0:
            findings["render_blocking_js"].append(
                {"page": url, "count": p["render_blocking_js"]})
        if p.get("render_blocking_css", 0) > 2:
            findings["render_blocking_css"].append(
                {"page": url, "count": p["render_blocking_css"]})

        if p.get("images_missing_dimensions", 0) > 0:
            findings["images_missing_dimensions"].append(
                {"page": url, "count": p["images_missing_dimensions"],
                 "of_total": p.get("image_count")})

        dom = p.get("dom_nodes", 0)
        if dom > args.dom_budget:
            findings["excessive_dom"].append({"page": url, "dom_nodes": dom})

        if w.get("requests", 0) > 80:
            findings["too_many_requests"].append({"page": url, "requests": w["requests"]})

        if w.get("js_bytes", 0) > args.js_budget:
            findings["large_js"].append({"page": url, "js_bytes": w["js_bytes"]})
        if w.get("css_bytes", 0) > args.css_budget:
            findings["large_css"].append({"page": url, "css_bytes": w["css_bytes"]})

        if not p.get("has_viewport"):
            findings["missing_viewport"].append({"page": url})

        if p.get("third_party_origins") and p.get("resource_hints", {}).get("preconnect", 0) == 0:
            findings["missing_preconnect"].append(
                {"page": url, "third_party_origins": p["third_party_origins"]})

        if (p.get("image_count", 0) > 5
                and p.get("images_no_lazy", 0) == p.get("image_count", 0)):
            findings["no_lazy_loading"].append(
                {"page": url, "image_count": p["image_count"]})

    # Escalate severity for the worst cases.
    severity = {
        "psi_poor_lcp": "high", "psi_poor_cls": "high", "psi_poor_inp": "high",
        "psi_low_score": "high", "no_text_compression": "high", "lcp_image_lazy": "high",
        "slow_ttfb": "high", "excessive_dom": "high",
        "page_weight_over_budget": "medium", "render_blocking_js": "medium",
        "render_blocking_css": "medium", "images_missing_dimensions": "medium",
        "too_many_requests": "medium", "large_js": "medium", "missing_viewport": "medium",
        "missing_preconnect": "low", "large_css": "low", "no_lazy_loading": "low",
    }

    analyzed = sum(1 for p in pages.values() if p.get("status") == 200)
    summary = {
        "pages_analyzed": analyzed,
        "psi_enabled": data.get("psi_enabled", False),
        "psi_strategy": data.get("psi_strategy"),
        "median_page_weight_bytes": (sorted(weights)[len(weights) // 2] if weights else 0),
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
