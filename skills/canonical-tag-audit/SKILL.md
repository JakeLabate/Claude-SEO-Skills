---
name: canonical-tag-audit
description: Audit a website's rel=canonical tags for SEO. Crawls pages and probes each canonical target to find missing canonicals, multiple conflicting canonicals, canonicals pointing at non-200 or redirecting or noindexed URLs, relative (non-absolute) canonicals, cross-host canonicals, https-to-http protocol downgrades, conflicts between the HTTP Link header and the in-page canonical, and canonicals containing fragments. Use when the user asks to audit, check, validate, or fix canonical tags, rel=canonical, duplicate-content consolidation, or canonicalization on a website.
---

# Canonical Tag Audit

Audit a website's `rel="canonical"` tags and produce an actionable SEO report.

## When to use this skill

Use this skill when the user asks to:

- Audit, validate, or check `rel="canonical"` tags / canonicalization
- Find pages with missing, duplicate, or conflicting canonicals
- Find canonicals that point at dead, redirecting, or noindexed URLs
- Diagnose duplicate-content consolidation problems
- Verify canonicals are absolute, same-host, and `https://`

## Inputs to collect

Before starting, confirm with the user:

1. **Site URL or URL list** — a live site root to crawl (auto-seeds from
   `/sitemap.xml`), or a text file of URLs with `--url-list`.
2. **Scope** — how many pages to crawl (default 500, cap with `--max-pages`).
3. **Probing** — whether to probe each canonical target's status/redirect/noindex
   (default on; `--no-probe` for a fast structural-only pass).

> **The indexable contract:** a canonical should point at a final, canonical,
> indexable `200` URL — ideally the page itself. A canonical that 404s, redirects,
> or is noindexed breaks consolidation and can drop the page from the index.

## Workflow

### Step 1: Crawl and probe canonicals

Use `scripts/extract_canonicals.py`:

```bash
python3 scripts/extract_canonicals.py https://example.com --max-pages 500 --output canonical_inventory.json
# already crawled once (e.g. in a full SEO audit)? skip the crawl and reuse the shared cache:
# python3 scripts/fetch_pages.py https://example.com --output page_cache.json
# python3 scripts/extract_canonicals.py --from-cache page_cache.json --output canonical_inventory.json
```

It records each page's status, every in-page `<link rel="canonical">` (raw href +
resolved URL), the `Link: rel="canonical"` header, meta robots, and
`X-Robots-Tag`, then probes each unique canonical target once for status,
redirect, and noindex.

### Step 2: Run the audit checks

Use `scripts/audit_canonicals.py`:

```bash
python3 scripts/audit_canonicals.py canonical_inventory.json --output audit_report.json
```

### Step 3: Evaluate the audit checks

Evaluate each check in `references/audit-checks.md`. Core checks:

| Check | Severity |
|---|---|
| Missing canonical on an indexable page | High |
| Multiple conflicting canonicals | High |
| Canonical points to a non-200 URL | High |
| Canonical points to a redirect | High |
| Canonical points to a noindex URL | Medium |
| Relative (non-absolute) canonical | Medium |
| Cross-host canonical | Medium |
| Protocol downgrade (https→http) in canonical | Medium |
| Header / HTML canonical conflict | Medium |
| Canonical contains a fragment | Low |
| Non-self canonical (confirm intent) | Info |

### Step 4: Produce the report

Write a report following `references/report-template.md`: summary by severity,
high-severity issues first, a section of non-self canonicals to confirm, and a
prioritized action list.

### Step 5: Recommend fixes

- **Missing:** add a self-referencing absolute `https://` canonical.
- **Non-200 / redirect target:** repoint at the final live `200` URL.
- **Multiple / header conflict:** emit exactly one canonical (find the duplicate
  CMS/plugin source).
- **Relative / cross-host / protocol downgrade:** rewrite to an absolute,
  same-host, `https://` URL.
- **Non-self canonicals:** confirm each consolidation is intentional.
- Base every recommendation on observed data; do not invent target statuses.

## Optional: export the report

### As a Word document (.docx)

If the user wants the report as a `.docx` (for example, to share with stakeholders or attach to a ticket), save the Markdown report to a file and convert it:

```bash
python3 scripts/md_to_docx.py report.md --output report.docx
```

`scripts/md_to_docx.py` uses only the Python standard library (no `pip install`) and renders headings, tables, lists, links, bold/italic, and code blocks. Offer this whenever a user asks for a Word doc, a `.docx`, or a shareable/downloadable report.

### As a CSV of findings (.csv)

If the user wants the raw findings as a spreadsheet (for filtering, sorting, or triage in Sheets or Excel), convert the audit's `audit_report.json` directly:

```bash
python3 scripts/findings_to_csv.py audit_report.json --output findings.csv
```

`scripts/findings_to_csv.py` is also standard-library only. It writes one row per finding, with `check` and `severity` columns prepended and list fields (e.g. the pages sharing a duplicate value) joined with `; `. Unlike the `.docx`, which reformats the written report, the CSV is a direct dump of the structured findings — offer it whenever a user wants the data itself, a spreadsheet, or to slice findings by check or severity.

## Resources

- `scripts/md_to_docx.py` — convert the Markdown report into a Word (.docx) document (standard library only)
- `scripts/findings_to_csv.py` — flatten the audit findings JSON into a CSV, one row per finding (standard library only)
- `references/audit-checks.md` — full definitions, thresholds, and rationale
- `references/report-template.md` — report output structure
- `scripts/extract_canonicals.py` — crawl pages and probe canonical targets
- `scripts/audit_canonicals.py` — run audit checks against the inventory
