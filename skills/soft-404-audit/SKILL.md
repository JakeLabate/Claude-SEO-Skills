---
name: soft-404-audit
description: Audit a website for soft 404s — pages that return HTTP 200 but are really "not found", empty, or error pages. Crawls pages and sends a missing-page probe to find error pages served with a 200 status, a server that returns 200 for every unknown URL instead of a real 404/410, thin pages matching the site's error template, and empty/near-empty pages. Use when the user asks to audit, check, or fix soft 404s, soft 404 errors in Search Console, pages that should be 404 but return 200, fake/empty pages, or missing pages that don't return the right status code.
---

# Soft 404 Audit

Audit a website for soft 404s and produce an actionable report. A soft 404 is a
page that returns `200 OK` but is really a "not found"/empty page — it wastes
crawl budget and can get real URLs dropped from the index.

## When to use this skill

Use this skill when the user asks to:

- Audit or fix soft 404s (including Search Console "Soft 404" reports)
- Find pages that return 200 but should return 404/410
- Check whether the site returns a real 404 for missing URLs
- Find empty or error-template pages served as live pages

## Inputs to collect

1. **Site URL or URL list** — a live site root to crawl (auto-seeds from
   `/sitemap.xml`), or a text file with `--url-list`. A URL list of the pages
   Search Console flagged works well.
2. **Scope** — pages to crawl (default 500, `--max-pages`).
3. **Thin threshold** — word count below which a 200 page is "thin" (default 50,
   `--thin-words`); raise it for content-heavy sites.

## Workflow

### Step 1: Crawl and probe

Use `scripts/extract_pages.py`:

```bash
python3 scripts/extract_pages.py https://example.com --max-pages 500 --output soft404_inventory.json
# already crawled once (e.g. in a full SEO audit)? skip the crawl and reuse the shared cache:
# python3 scripts/fetch_pages.py https://example.com --output page_cache.json
# python3 scripts/extract_pages.py --from-cache page_cache.json --output soft404_inventory.json
```

It records each page's status, title, first H1, visible word count, and whether
error phrases appear in the title/H1, then sends one request to a deliberately
non-existent URL to learn how the site handles missing pages.

### Step 2: Run the audit checks

```bash
python3 scripts/audit_soft404.py soft404_inventory.json --output audit_report.json
```

### Step 3: Evaluate the audit checks

Evaluate each check in `references/audit-checks.md`. Core checks:

| Check | Severity |
|---|---|
| Soft 404 (error page served as 200) | High |
| Missing URLs return 200 (site-wide) | High |
| Thin page matching the error template | Medium |
| Empty / near-empty page | Low |

### Step 4: Produce the report

Write a report following `references/report-template.md`: lead with the site-wide
status-code behavior, then confirmed soft 404s, then suspected ones, and a
prioritized action list.

### Step 5: Recommend fixes

- **Missing URLs return 200:** configure the server/framework to return a real
  `404` for unmatched routes (render the custom 404 page *with* a 404 status).
  This single fix clears the whole class.
- **Confirmed soft 404:** return `404` (or `410` if permanently gone), or restore
  the page if the URL should resolve.
- **Thin/empty pages:** verify they aren't JavaScript-rendered (this crawler
  doesn't run JS); add content or noindex genuine placeholders.
- Base every recommendation on observed signals; never invent page content.

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
- `references/audit-checks.md` — full definitions and rationale
- `references/report-template.md` — report output structure
- `scripts/extract_pages.py` — crawl pages and probe missing-page behavior
- `scripts/audit_soft404.py` — run soft-404 audit checks
