---
name: keyword-cannibalization-audit
description: Audit a website for keyword cannibalization — multiple pages competing for the same search query. Crawls pages and compares titles, H1s, and body keywords to find pages with duplicate title targets, clusters of pages whose keyword signatures overlap, and pages sharing the same primary keyword phrase. Use when the user asks to audit, check, or fix keyword cannibalization, pages competing for the same keyword, overlapping/competing content, keyword overlap, or which page should rank for a query on a website.
---

# Keyword Cannibalization Audit

Audit a website for pages that compete with each other for the same query, and
produce an actionable report. Findings are *candidates to confirm* — some overlap
is legitimate; this skill surfaces the clusters and recommends a hierarchy.

## When to use this skill

Use this skill when the user asks to:

- Audit or fix keyword cannibalization
- Find pages competing for the same keyword / query
- Decide which page should rank for a topic and what to do with the rest
- Review overlapping or competing content

## Inputs to collect

1. **Site URL or URL list** — a live site root to crawl (auto-seeds from
   `/sitemap.xml`), or a text file with `--url-list`.
2. **Scope** — pages to crawl (default 500, `--max-pages`).
3. **Brand suffix** — e.g. `"| Acme Co"` so brand words don't inflate title
   similarity (`--brand-suffix`).
4. **Overlap threshold** — Jaccard similarity to flag competing pages (default
   0.6, `--overlap`).

## Workflow

### Step 1: Crawl and capture target signals

Use `scripts/extract_targets.py`:

```bash
python3 scripts/extract_targets.py https://example.com --max-pages 500 --output target_inventory.json
```

For each page it records title, H1, meta description, noindex, word count, and the
top body keywords by frequency.

### Step 2: Run the audit checks

```bash
python3 scripts/audit_cannibalization.py target_inventory.json --brand-suffix "| Acme Co" --overlap 0.6 --output audit_report.json
```

### Step 3: Evaluate the audit checks

Evaluate each check in `references/audit-checks.md`. Core checks:

| Check | Severity |
|---|---|
| Duplicate title target | High |
| Overlapping target cluster (keyword signatures) | Medium |
| Shared primary keyword (title bigram) | Low |

### Step 4: Produce the report

Write a report following `references/report-template.md`: summary, duplicate title
targets first, then overlapping clusters (largest first) each with a recommended
hierarchy, and a prioritized action list.

### Step 5: Recommend fixes

- For each cluster, name **one primary page** and a role for every other page:
  differentiate to a distinct sub-query, merge, or 301/canonicalize into the
  primary.
- **Frame as hierarchy, not deletion** — supporting pages that target distinct
  intents and link up to the primary are healthy.
- **Always recommend confirming with Search Console** query data before
  consolidating: this audit infers competition from on-page signals.
- Related angles: `meta-data-audit` (duplicate titles) and
  `content-quality-audit` (duplicate bodies).
- Base every grouping on observed signatures; never invent rankings.

## Optional: export the report as a Word document

If the user wants the findings as a `.docx` (for example, to share with stakeholders or attach to a ticket), save the Markdown report to a file and convert it:

```bash
python3 scripts/md_to_docx.py report.md --output report.docx
```

`scripts/md_to_docx.py` uses only the Python standard library (no `pip install`) and renders headings, tables, lists, links, bold/italic, and code blocks. Offer this whenever a user asks for a Word doc, a `.docx`, or a shareable/downloadable report.

## Resources

- `scripts/md_to_docx.py` — convert the Markdown report into a Word (.docx) document (standard library only)
- `references/audit-checks.md` — full definitions, thresholds, and rationale
- `references/report-template.md` — report output structure
- `scripts/extract_targets.py` — crawl and capture keyword-target signals
- `scripts/audit_cannibalization.py` — run cannibalization audit checks
