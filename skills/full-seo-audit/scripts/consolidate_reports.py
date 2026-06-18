#!/usr/bin/env python3
"""Merge multiple per-skill audit_report.json files into one consolidated report.

Each individual audit skill writes an audit report shaped like:

    { "summary": {...}, "severity": {"<check>": "high"|"medium"|"low"|"info", ...},
      "findings": {"<check>": [ ... ], ...} }

This script reads several of those (by file, glob, or directory) and produces a
single cross-skill view: total issues by severity, a per-skill breakdown, and a
flat, severity-ranked list of every failing check.

Usage:
    python3 consolidate_reports.py report1.json report2.json ... [--output consolidated.json]
    python3 consolidate_reports.py --dir ./audits [--output consolidated.json]

The skill name for each report is inferred from the filename (e.g.
`sitemap-audit.audit_report.json` or `sitemap_audit_report.json` -> "sitemap").
Override per file with `name=path`:

    python3 consolidate_reports.py sitemap=sm.json meta=md.json

Uses only the Python standard library.
"""

import argparse
import glob
import json
import os
import sys

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}


def infer_name(path):
    base = os.path.basename(path)
    for suffix in (".audit_report.json", "_audit_report.json", ".report.json",
                   "_report.json", ".json"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    return base.replace("_", "-").replace(".", "-") or "report"


def load_report(name, path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"  skipped {path}: {e}", file=sys.stderr)
        return None
    severity = data.get("severity", {})
    findings = data.get("findings", {})
    checks = []
    for check, items in findings.items():
        count = len(items) if isinstance(items, list) else int(bool(items))
        if count == 0:
            continue
        checks.append({
            "skill": name,
            "check": check,
            "severity": severity.get(check, "info"),
            "count": count,
        })
    return checks


def main():
    ap = argparse.ArgumentParser(description="Consolidate per-skill audit reports.")
    ap.add_argument("reports", nargs="*",
                    help="Report JSON files, optionally as name=path. Or use --dir.")
    ap.add_argument("--dir", help="Directory to scan for *report*.json files")
    ap.add_argument("--output", default="consolidated_report.json")
    args = ap.parse_args()

    inputs = []  # (name, path)
    for token in args.reports:
        if "=" in token and not os.path.exists(token):
            name, path = token.split("=", 1)
            inputs.append((name, path))
        else:
            for path in glob.glob(token) or [token]:
                inputs.append((infer_name(path), path))
    if args.dir:
        for path in sorted(glob.glob(os.path.join(args.dir, "*report*.json"))):
            inputs.append((infer_name(path), path))

    if not inputs:
        ap.error("no report files given (pass files or --dir)")

    all_checks = []
    per_skill = {}
    for name, path in inputs:
        checks = load_report(name, path)
        if checks is None:
            continue
        all_checks.extend(checks)
        bucket = per_skill.setdefault(name, {"high": 0, "medium": 0, "low": 0, "info": 0})
        for c in checks:
            bucket[c["severity"]] = bucket.get(c["severity"], 0) + c["count"]

    all_checks.sort(key=lambda c: (SEVERITY_ORDER.get(c["severity"], 9),
                                   -c["count"], c["skill"], c["check"]))

    totals = {"high": 0, "medium": 0, "low": 0, "info": 0}
    for c in all_checks:
        totals[c["severity"]] = totals.get(c["severity"], 0) + c["count"]

    consolidated = {
        "summary": {
            "skills_audited": sorted(per_skill),
            "issues_by_severity": totals,
            "total_issues": sum(totals.values()),
            "per_skill": per_skill,
        },
        "checks_ranked": all_checks,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(consolidated, f, indent=2, ensure_ascii=False)

    print(json.dumps(consolidated["summary"], indent=2))
    print(f"\nConsolidated {len(per_skill)} report(s), "
          f"{consolidated['summary']['total_issues']} total issues, "
          f"written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
