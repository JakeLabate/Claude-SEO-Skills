#!/usr/bin/env python3
"""Audit a resource inventory (from extract_resources.py) for mixed content.

Usage:
    python3 audit_resources.py resource_inventory.json [--output audit_report.json]

Checks (see references/audit-checks.md):
- active_mixed_content (high): http script/stylesheet/iframe/object on an https page
- insecure_form_action (high): a form on an https page POSTs/GETs to http://
- passive_mixed_content (medium): http img/audio/video/source on an https page
- protocol_relative_resource (low): // resource URLs (legacy; should be https://)
- insecure_page (info): the page itself was served over http://

Only pages served over https are checked for mixed content (http pages have no
"mixed" content — they are wholly insecure, reported separately as insecure_page).

Uses only the Python standard library.
"""

import argparse
import json
import sys
import urllib.parse


def main():
    ap = argparse.ArgumentParser(description="Run mixed-content audit checks.")
    ap.add_argument("inventory")
    ap.add_argument("--output", default="audit_report.json")
    args = ap.parse_args()

    with open(args.inventory, encoding="utf-8") as f:
        data = json.load(f)
    pages = data.get("pages", {})

    findings = {k: [] for k in (
        "active_mixed_content", "insecure_form_action", "passive_mixed_content",
        "protocol_relative_resource", "insecure_page")}

    for url, page in pages.items():
        if page.get("status", 0) == 0:
            continue
        final_url = page.get("final_url", url)
        page_https = final_url.startswith("https://")

        if not page_https and final_url.startswith("http://"):
            findings["insecure_page"].append({"page": url})
            # http pages aren't "mixed"; skip per-resource mixed checks
            continue

        for r in page.get("resources", []):
            scheme = r.get("scheme")
            entry = {"page": url, "tag": r["tag"], "attr": r["attr"], "resource": r["url"]}
            if r.get("protocol_relative"):
                findings["protocol_relative_resource"].append(entry)
                continue
            if scheme != "http":
                continue
            if r["kind"] == "form":
                findings["insecure_form_action"].append(entry)
            elif r["kind"] == "active":
                findings["active_mixed_content"].append(entry)
            else:
                findings["passive_mixed_content"].append(entry)

    severity = {
        "active_mixed_content": "high", "insecure_form_action": "high",
        "passive_mixed_content": "medium",
        "protocol_relative_resource": "low", "insecure_page": "info",
    }
    pages_with_mixed = len({f["page"] for k in
                            ("active_mixed_content", "passive_mixed_content",
                             "insecure_form_action") for f in findings[k]})
    summary = {
        "pages_analyzed": sum(1 for p in pages.values() if p.get("status", 0) != 0),
        "pages_with_mixed_content": pages_with_mixed,
        "issues_by_check": {k: len(v) for k, v in findings.items()},
        "issues_by_severity": {
            level: sum(len(findings[k]) for k, s in severity.items() if s == level)
            for level in ("high", "medium", "low", "info")},
    }
    report = {"summary": summary, "severity": severity, "findings": findings}
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(json.dumps(summary, indent=2))
    print(f"Full report written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
