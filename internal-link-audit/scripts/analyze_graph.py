#!/usr/bin/env python3
"""Analyze an internal link graph JSON (from crawl_links.py) and emit audit findings.

Usage:
    python3 analyze_graph.py link_graph.json [--output audit_report.json]

Checks implemented (see references/audit-checks.md):
- broken_links: internal links to 4xx/5xx targets (high)
- orphan_pages: crawled pages with zero inbound internal links (high)
- redirected_links: internal links to 3xx targets (medium)
- deep_pages: pages with click depth > 3 (medium)
- generic_anchors: weak anchor text (medium)
- noncanonical_targets: links to pages whose canonical differs or are noindexed (medium)
- excessive_outlinks: pages with > 150 outgoing internal links (low)
- nofollow_internal: internal links with rel nofollow/sponsored/ugc (low)

Uses only the Python standard library.
"""

import argparse
import json
import sys
from collections import Counter

GENERIC_ANCHORS = {
    "click here", "here", "read more", "learn more", "more",
    "this page", "link", "this", "continue", "view", "see more", "",
}
MAX_DEPTH = 3
MAX_OUTLINKS = 150


def main():
    ap = argparse.ArgumentParser(description="Run internal link audit checks on a link graph.")
    ap.add_argument("graph", help="link_graph.json from crawl_links.py")
    ap.add_argument("--output", default="audit_report.json")
    args = ap.parse_args()

    with open(args.graph) as f:
        data = json.load(f)
    pages = data["pages"]
    statuses = data.get("statuses", {})

    inbound = Counter()
    for src, page in pages.items():
        for link in page["links"]:
            if link["target"] != src:
                inbound[link["target"]] += 1

    findings = {
        "broken_links": [], "orphan_pages": [], "redirected_links": [],
        "deep_pages": [], "generic_anchors": [], "noncanonical_targets": [],
        "excessive_outlinks": [], "nofollow_internal": [],
    }

    home_depth0 = min((p["depth"] for p in pages.values()), default=0)

    for src, page in pages.items():
        if len(page["links"]) > MAX_OUTLINKS:
            findings["excessive_outlinks"].append(
                {"page": src, "outgoing_links": len(page["links"])})
        if page["depth"] - home_depth0 > MAX_DEPTH:
            findings["deep_pages"].append({"page": src, "depth": page["depth"]})

        for link in page["links"]:
            target, anchor = link["target"], link["anchor"]
            status = statuses.get(target)
            entry = {"source": src, "target": target, "anchor": anchor}

            if status is not None:
                if status >= 400 or status == 0:
                    findings["broken_links"].append({**entry, "status": status})
                elif 300 <= status < 400:
                    findings["redirected_links"].append({**entry, "status": status})

            if anchor.lower().strip() in GENERIC_ANCHORS:
                findings["generic_anchors"].append(entry)

            rel = (link.get("rel") or "").lower()
            if any(r in rel for r in ("nofollow", "sponsored", "ugc")):
                findings["nofollow_internal"].append({**entry, "rel": link["rel"]})

            tpage = pages.get(target)
            if tpage:
                robots = (tpage.get("meta_robots") or "").lower()
                canonical = tpage.get("canonical")
                if "noindex" in robots:
                    findings["noncanonical_targets"].append({**entry, "reason": "noindex"})
                elif canonical and canonical.rstrip("/") != target.rstrip("/"):
                    findings["noncanonical_targets"].append(
                        {**entry, "reason": "canonical points elsewhere",
                         "canonical": canonical})

    for url, page in pages.items():
        if inbound[url] == 0 and page["depth"] > home_depth0:
            findings["orphan_pages"].append({"page": url})

    severity = {
        "broken_links": "high", "orphan_pages": "high",
        "redirected_links": "medium", "deep_pages": "medium",
        "generic_anchors": "medium", "noncanonical_targets": "medium",
        "excessive_outlinks": "low", "nofollow_internal": "low",
    }
    summary = {
        "pages_analyzed": len(pages),
        "total_internal_links": sum(len(p["links"]) for p in pages.values()),
        "issues_by_check": {k: len(v) for k, v in findings.items()},
        "issues_by_severity": {
            level: sum(len(findings[k]) for k, s in severity.items() if s == level)
            for level in ("high", "medium", "low")
        },
    }
    report = {"summary": summary, "severity": severity, "findings": findings,
              "inbound_link_counts": dict(inbound)}

    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(summary, indent=2))
    print(f"Full report written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
