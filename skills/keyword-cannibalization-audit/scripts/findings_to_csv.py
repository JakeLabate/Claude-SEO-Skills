#!/usr/bin/env python3
"""Flatten an audit_report.json into a flat findings.csv.

Standard-library only — no pip install. Every auditor in this repo writes an
``audit_report.json`` shaped like::

    {
      "summary": {...},
      "severity": {"<check>": "High|Medium|Low|Info", ...},
      "findings": {"<check>": [ {<fact>}, {<fact>}, ... ], ...}
    }

This turns that into one row per finding, with the check's severity resolved
from the ``severity`` map, so the report's findings open directly in a
spreadsheet — filter by severity, sort by check, hand it to a client.

This is the canonical copy. An identical copy lives in every skill's scripts/
folder so each skill stays self-contained (the installer copies skill folders
individually). tools/validate_skills.py asserts the copies match this file.

Usage:
    python3 findings_to_csv.py audit_report.json --output findings.csv
    python3 findings_to_csv.py audit_report.json -o findings.csv
    cat audit_report.json | python3 findings_to_csv.py - -o findings.csv
    python3 findings_to_csv.py audit_report.json -o -   # write CSV to stdout
"""

import argparse
import csv
import json
import sys

# Lead with what matters most, mirroring how the reports are ordered.
SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2, "info": 3}

# Columns that, when present, read best near the front of the row.
PREFERRED_KEYS = [
    "skill",
    "url", "page", "src", "sitemap", "loc", "from", "to", "target",
    "title", "h1", "alt", "canonical", "status", "final_url",
    "length", "count",
]


def stringify(value):
    """Render a finding value as a single CSV cell."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (str, int, float)):
        return str(value)
    if isinstance(value, list):
        return "; ".join(
            stringify(v) if isinstance(v, (dict, list)) else str(v) for v in value
        )
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def iter_rows(report):
    """Yield a flat row dict per finding, handling both report shapes.

    Per-skill auditors write ``{"severity": {check: level}, "findings":
    {check: [fact, ...]}}``. The full-seo-audit orchestrator writes a
    consolidated ``{"checks_ranked": [{skill, check, severity, count}, ...]}``.
    Both flatten to one row per finding/check.
    """
    severity_map = report.get("severity", {}) or {}
    findings = report.get("findings", {})
    if isinstance(findings, dict):
        for check, items in findings.items():
            sev = severity_map.get(check, "")
            if isinstance(items, dict):
                items = [items]
            elif not isinstance(items, list):
                items = [{"value": items}]
            for item in items:
                if not isinstance(item, dict):
                    item = {"value": item}
                row = {"severity": sev, "check": check}
                for key, value in item.items():
                    if key not in ("severity", "check"):
                        row[key] = value
                yield row

    checks_ranked = report.get("checks_ranked")
    if isinstance(checks_ranked, list):
        for entry in checks_ranked:
            if not isinstance(entry, dict):
                continue
            row = {"severity": entry.get("severity", ""), "check": entry.get("check", "")}
            for key, value in entry.items():
                if key not in ("severity", "check"):
                    row[key] = value
            yield row


def build_rows(report):
    """Return (columns, rows) for the report's findings, severity-ordered."""
    rows = []
    extra_keys = []
    seen = set()
    for row in iter_rows(report):
        for key in list(row):
            if key not in ("severity", "check"):
                row[key] = stringify(row[key])
                if key not in seen:
                    seen.add(key)
                    extra_keys.append(key)
        rows.append(row)

    ordered_extra = [k for k in PREFERRED_KEYS if k in seen]
    ordered_extra += sorted(k for k in extra_keys if k not in PREFERRED_KEYS)
    columns = ["severity", "check"] + ordered_extra

    rows.sort(key=lambda r: (
        SEVERITY_RANK.get(str(r.get("severity", "")).lower(), 99),
        r.get("check", ""),
        r.get("url", "") or r.get("page", ""),
    ))
    return columns, rows


def write_csv(report, out):
    columns, rows = build_rows(report)
    writer = csv.DictWriter(out, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return len(rows)


def main():
    ap = argparse.ArgumentParser(description="Flatten an audit_report.json into findings.csv")
    ap.add_argument("input", help="audit_report.json file, or '-' to read stdin")
    ap.add_argument("-o", "--output", required=True, help="output .csv path, or '-' for stdout")
    args = ap.parse_args()

    if args.input == "-":
        report = json.load(sys.stdin)
    else:
        with open(args.input, "r", encoding="utf-8") as f:
            report = json.load(f)

    if args.output == "-":
        count = write_csv(report, sys.stdout)
    else:
        # newline="" is required for the csv module to emit correct line endings.
        with open(args.output, "w", encoding="utf-8", newline="") as f:
            count = write_csv(report, f)
        print("Wrote %s (%d finding(s))" % (args.output, count), file=sys.stderr)


if __name__ == "__main__":
    main()
