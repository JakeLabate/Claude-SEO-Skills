---
name: content-quality-audit
description: Audit a website's content quality for SEO. Crawls pages and measures visible word count, text-to-HTML ratio, and content fingerprints to find thin content, exact duplicate body text across pages, near-duplicate (templated/boilerplate) pages, pages that are mostly markup with little text, and pages missing an H1. Use when the user asks to audit, check, or fix thin content, duplicate or near-duplicate content, low-value pages, content depth, doorway pages, or text-to-HTML ratio on a website.
---

# Content Quality Audit

Audit a website's content for thinness and duplication, and produce an actionable
report. These checks surface pages unlikely to rank or add value; they are signals
for human review, calibrated to the site.

## When to use this skill

Use this skill when the user asks to:

- Audit or fix thin / low-value content
- Find duplicate or near-duplicate pages (templated/boilerplate content)
- Check content depth or text-to-HTML ratio
- Identify doorway-style pages

## Inputs to collect

1. **Site URL or URL list** — a live site root to crawl (auto-seeds from
   `/sitemap.xml`), or a text file with `--url-list`.
2. **Scope** — pages to crawl (default 500, `--max-pages`).
3. **Thresholds** — `--thin-words` (default 300) and `--similarity` (default
   0.85). Calibrate to the content type before running.

## Workflow

### Step 1: Crawl and measure content

Use `scripts/extract_content.py`:

```bash
python3 scripts/extract_content.py https://example.com --max-pages 500 --output content_inventory.json
# already crawled once (e.g. in a full SEO audit)? skip the crawl and reuse the shared cache:
# python3 scripts/fetch_pages.py https://example.com --output page_cache.json
# python3 scripts/extract_content.py --from-cache page_cache.json --output content_inventory.json
```

For each page it records visible word count, text-to-HTML ratio, title, H1,
noindex, an exact content hash, and a 32-value MinHash signature for fast
near-duplicate detection.

### Step 2: Run the audit checks

```bash
python3 scripts/audit_content.py content_inventory.json --thin-words 300 --similarity 0.85 --output audit_report.json
```

### Step 3: Evaluate the audit checks

Evaluate each check in `references/audit-checks.md`. Core checks:

| Check | Severity |
|---|---|
| Thin content (below word threshold) | High |
| Duplicate content (identical body) | High |
| Near-duplicate content (high MinHash similarity) | Medium |
| Low text-to-HTML ratio | Medium |
| Missing H1 | Low |

### Step 4: Produce the report

Write a report following `references/report-template.md`: summary with the median
word count for calibration, thin and duplicate content first, near-duplicate
clusters grouped as patterns, and a prioritized action list.

### Step 5: Recommend fixes

- **Thin content:** expand with useful content, consolidate several thin pages, or
  `noindex` pages that exist for non-search reasons.
- **Duplicate/near-duplicate:** canonicalize to one URL, consolidate, or add
  substantial unique content (cross-check `canonical-tag-audit`).
- **Low ratio:** increase real content or trim boilerplate markup.
- **Missing H1:** add one descriptive H1 (see `heading-structure-audit`).
- **Always caveat JavaScript-rendered pages** — this crawler doesn't run JS, so
  verify a flagged page isn't simply rendered client-side.
- Base every recommendation on the measured signals; never invent content.

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
- `references/audit-checks.md` — full definitions, thresholds, and rationale
- `references/report-template.md` — report output structure
- `scripts/extract_content.py` — crawl and measure content signals
- `scripts/audit_content.py` — run content-quality audit checks
