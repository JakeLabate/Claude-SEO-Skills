---
name: pagination-audit
description: Audit a website's pagination (paginated blog listings, category pages, and search results) for SEO. Crawls pages and inspects canonical tags, meta robots, rel=next/prev, and page-number URL patterns to find paginated pages that canonicalize to page 1 (hiding deep content from the index), noindexed component pages, paginated pages missing a self-canonical, broken or inconsistent rel=next/prev, and redundant ?page=1 first pages. Use when the user asks to audit, check, or fix pagination, paginated pages, rel=next/prev, page 2 indexing, infinite scroll SEO, or category/listing pagination on a website.
---

# Pagination Audit

Audit a website's paginated series and produce an actionable SEO report focused on
keeping deep, paginated content indexable.

## When to use this skill

Use this skill when the user asks to:

- Audit or fix pagination on blog/category/search listings
- Diagnose why page 2+ of a listing isn't indexed
- Check `rel="next"` / `rel="prev"` and canonical handling on paginated pages
- Review infinite-scroll / "load more" SEO

## Inputs to collect

1. **Site URL or URL list** — a live site root to crawl (auto-seeds from
   `/sitemap.xml`), or a text file with `--url-list`. Include listing pages with
   their `?page=`/`/page/N/` URLs so the crawler sees the series.
2. **Scope** — pages to crawl (default 500, `--max-pages`).

## Workflow

### Step 1: Crawl and inventory pagination signals

Use `scripts/extract_pagination.py`:

```bash
python3 scripts/extract_pagination.py https://example.com --max-pages 500 --output pagination_inventory.json
# already crawled once (e.g. in a full SEO audit)? skip the crawl and reuse the shared cache:
# python3 scripts/fetch_pages.py https://example.com --output page_cache.json
# python3 scripts/extract_pagination.py --from-cache page_cache.json --output pagination_inventory.json
```

It records each page's canonical, meta robots, `rel="next"`/`rel="prev"` targets,
and the page number detected from the URL (`?page=N`, `/page/N`, etc.).

### Step 2: Run the audit checks

```bash
python3 scripts/audit_pagination.py pagination_inventory.json --output audit_report.json
```

### Step 3: Evaluate the audit checks

Evaluate each check in `references/audit-checks.md`. Core checks:

| Check | Severity |
|---|---|
| Paginated page canonicalizes to page 1 | High |
| Paginated (page 2+) page is noindexed | Medium |
| Paginated page missing a self-canonical | Medium |
| Broken rel=next/prev target | Medium |
| Inconsistent rel=next/prev reciprocity | Low |
| First page carries a redundant ?page=1 | Low |
| rel=next/prev present (Google ignores it) | Info |

### Step 4: Produce the report

Write a report following `references/report-template.md`: summary by severity,
the canonical-to-page-1 issue first, then indexability and self-canonical gaps,
framed as template-level fixes, and a prioritized action list.

### Step 5: Recommend fixes

- **Canonical to page 1:** make each paginated page self-canonical.
- **Noindex on page 2+:** let component pages be indexable, or guarantee deep
  items are reachable (e.g. via the XML sitemap).
- **Missing self-canonical:** add a self-referencing canonical to every page.
- **Broken/inconsistent rel=next/prev:** fix the targets or remove them.
- **?page=1 duplicate:** serve page 1 at the bare URL and 301 `?page=1` to it.
- Frame fixes at the template level; base everything on observed data.

## Optional: export the report as a Word document or CSV

If the user wants the findings as a `.docx` (for example, to share with stakeholders or attach to a ticket), save the Markdown report to a file and convert it:

```bash
python3 scripts/md_to_docx.py report.md --output report.docx
```

`scripts/md_to_docx.py` uses only the Python standard library (no `pip install`) and renders headings, tables, lists, links, bold/italic, and code blocks. Offer this whenever a user asks for a Word doc, a `.docx`, or a shareable/downloadable report.

To hand the findings back as a spreadsheet instead, flatten the audit JSON to a CSV — one row per finding, with its severity:

```bash
python3 scripts/findings_to_csv.py audit_report.json --output findings.csv
```

`scripts/findings_to_csv.py` is standard-library only too. Offer it whenever a user asks for a CSV, a spreadsheet, or the full list of findings.

## Resources

- `scripts/md_to_docx.py` — convert the Markdown report into a Word (.docx) document (standard library only)
- `scripts/findings_to_csv.py` — flatten the audit report JSON into a flat findings.csv (standard library only)
- `references/audit-checks.md` — full definitions and rationale
- `references/report-template.md` — report output structure
- `scripts/extract_pagination.py` — crawl and inventory pagination signals
- `scripts/audit_pagination.py` — run pagination audit checks
