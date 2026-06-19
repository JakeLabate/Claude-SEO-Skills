#!/usr/bin/env python3
"""Flatten an audit_report.json findings block into a single CSV.

Standard-library only — no pip install. Every audit script in this repo writes
an audit_report.json with the same top-level shape:

    {"summary": {...},
     "severity": {"<check>": "high|medium|low|info"},
     "findings": {"<check>": [ {finding}, {finding}, ... ]}}

This tool reads that file and writes one row per finding, with `check` and
`severity` columns prepended so the whole report is sortable and filterable in
a spreadsheet. Columns are the union of every finding's fields, in first-seen
order. List-valued fields (e.g. the pages sharing a duplicate title) are joined
with "; "; dict-valued fields are JSON-encoded so nothing is silently dropped.

This is the canonical copy. An identical copy lives in every skill's scripts/
folder so each skill stays self-contained (the installer copies skill folders
individually). tools/sync_shared.py stamps it out and --check asserts the copies
match this file.

Usage:
    python3 findings_to_csv.py audit_report.json --output findings.csv
    python3 findings_to_csv.py audit_report.json -o findings.csv
    python3 findings_to_csv.py audit_report.json            # writes to stdout
    cat audit_report.json | python3 findings_to_csv.py -     # read from stdin
"""

import argparse
import csv
import json
import sys


def _stringify(value):
    """Render one finding field as a flat CSV cell.

    Lists become "a; b; c" (joining scalars, JSON-encoding anything richer);
    dicts are JSON-encoded; None becomes empty; scalars pass through.
    """
    if value is None:
        return ""
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, (dict, list)):
                parts.append(json.dumps(item, ensure_ascii=False, sort_keys=True))
            else:
                parts.append(str(item))
        return "; ".join(parts)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def flatten(report):
    """Return (fieldnames, rows) for the report's findings.

    Each row is a dict carrying `check`, `severity`, and the finding's own
    fields. Fieldnames lead with check/severity, then every field key in the
    order first encountered so related columns stay grouped.
    """
    findings = report.get("findings", {}) or {}
    severity = report.get("severity", {}) or {}

    field_order = []
    seen = set()
    rows = []
    for check in findings:
        for item in findings[check]:
            if not isinstance(item, dict):
                item = {"value": item}
            row = {"check": check, "severity": severity.get(check, "")}
            for key, value in item.items():
                if key not in seen:
                    seen.add(key)
                    field_order.append(key)
                row[key] = _stringify(value)
            rows.append(row)

    fieldnames = ["check", "severity"] + field_order
    return fieldnames, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report", help="audit_report.json (or - for stdin)")
    ap.add_argument("-o", "--output", help="CSV file to write (default: stdout)")
    args = ap.parse_args()

    if args.report == "-":
        report = json.load(sys.stdin)
    else:
        with open(args.report, encoding="utf-8") as f:
            report = json.load(f)

    fieldnames, rows = flatten(report)

    if args.output:
        out = open(args.output, "w", newline="", encoding="utf-8")
    else:
        out = sys.stdout
    try:
        writer = csv.DictWriter(out, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    finally:
        if args.output:
            out.close()

    if args.output:
        print(f"Wrote {len(rows)} finding(s) to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
