---
name: full-seo-audit
description: Run a complete technical-SEO audit of a website by orchestrating every individual audit (sitemap, robots.txt, redirects, internal links, external links, metadata, headings, images, schema markup, canonical tags, Open Graph, mixed content, pagination, soft 404s, content quality, keyword cannibalization, site architecture, Core Web Vitals, and llms.txt) and consolidating the results into one prioritized report. Use when the user asks for a full, complete, comprehensive, end-to-end, or site-wide SEO audit, a technical SEO review, or a single report covering many SEO issues at once.
---

# Full SEO Audit

Run the individual SEO audit skills, then merge their findings into one
consolidated, prioritized report. This skill is the orchestrator; the real work
is done by the per-area skills it coordinates.

## When to use this skill

Use this when the user wants the whole picture rather than one area:

- "Run a full / complete / comprehensive SEO audit of example.com"
- "Do a technical SEO review of my site"
- "Give me one report covering everything that's wrong with my SEO"

For a single area ("check my sitemap", "audit my titles"), use that area's skill
directly instead.

## Inputs to collect

1. **Site URL** — the live site root (e.g., `https://example.com`).
2. **Scope** — how many pages to crawl (default ~200) and how many sitemap URLs
   to probe. Larger sites should be sampled.
3. **Focus** — run everything (default), or a chosen subset (e.g., "just
   crawlability and indexation"). Map the user's intent to the skills below.
4. **API key (optional)** — Core Web Vitals field data needs a Google PageSpeed
   Insights key; without it, that audit uses lab proxies only.

## Coverage map

Each row is a separate skill. Run the ones in scope.

| Area | Skill | Crawls / fetches |
|---|---|---|
| Indexation: sitemaps | `sitemap-audit` | XML sitemaps |
| Crawlability: robots.txt | `robots-txt-audit` | robots.txt |
| Crawlability: architecture | `site-architecture-audit` | site + robots + sitemap |
| Redirects | `redirect-audit` | URL list / crawl |
| Internal links | `internal-link-audit` | crawl |
| External links | `external-link-audit` | crawl |
| Canonical tags | `canonical-tag-audit` | crawl |
| Pagination | `pagination-audit` | crawl |
| Soft 404s | `soft-404-audit` | crawl |
| Titles & descriptions | `meta-data-audit` | crawl |
| Headings | `heading-structure-audit` | crawl |
| Images | `image-seo-audit` | crawl |
| Structured data | `schema-markup-audit` | crawl |
| Social metadata | `open-graph-audit` | crawl |
| Content quality | `content-quality-audit` | crawl |
| Keyword cannibalization | `keyword-cannibalization-audit` | crawl |
| HTTPS / mixed content | `mixed-content-audit` | crawl |
| Page experience | `core-web-vitals-audit` | per-URL |
| AI discoverability | `llms-txt-audit` | /llms.txt |

## Workflow

### Step 1: Crawl once into a shared page cache

The page-based audits all read the same HTML, so crawl the site a **single**
time with the shared fetch stage and let every extractor read from that cache:

```bash
mkdir -p audits
python3 scripts/fetch_pages.py https://example.com --max-pages 200 --output audits/page_cache.json
```

### Step 2: Extract + audit each in-scope area

For each page-based area in scope, run its extractor with `--from-cache` (pure,
no extra crawl) then its audit script. Save each audit output to the shared
folder using a stable, skill-named filename so they can be merged:

```bash
# repeat per in-scope page-based skill — all read the ONE page_cache.json
python3 ../meta-data-audit/scripts/extract_metadata.py --from-cache audits/page_cache.json --output audits/meta.inventory.json
python3 ../meta-data-audit/scripts/audit_metadata.py audits/meta.inventory.json --output audits/meta-data-audit.audit_report.json

python3 ../heading-structure-audit/scripts/extract_headings.py --from-cache audits/page_cache.json --output audits/head.inventory.json
python3 ../heading-structure-audit/scripts/audit_headings.py audits/head.inventory.json --output audits/heading-structure-audit.audit_report.json
```

The skills that read `--from-cache` are: meta-data, heading-structure,
image-seo, schema-markup, open-graph, content-quality, keyword-cannibalization,
mixed-content, canonical-tag, pagination, soft-404, and external-link. (A few
also run a small secondary probe — canonical targets, share images, the soft-404
missing-page probe — on top of the cached crawl.)

The non-page audits fetch their own thing and don't use the page cache: run them
per their own `SKILL.md` — `sitemap-audit`, `robots-txt-audit`, `llms-txt-audit`,
`redirect-audit`, `core-web-vitals-audit`, plus `internal-link-audit` and
`site-architecture-audit` (which crawl with depth tracking of their own).

### Step 3: Consolidate

Merge every `*.audit_report.json` into one cross-skill view:

```bash
python3 scripts/consolidate_reports.py --dir audits --output consolidated_report.json
```

The consolidator emits total issues by severity, a per-skill breakdown, and a
flat list of every failing check ranked by severity then count.

### Step 4: Produce the consolidated report

Write the report following `references/report-template.md`:

1. **Executive summary** — overall health, issue counts by severity, the 3–5
   highest-impact fixes across all areas.
2. **Scorecard** — one row per audited area with its issue counts and a status.
3. **Findings by area** — a short section per skill summarizing its top issues
   and linking to (or inlining) that skill's own detailed report.
4. **Prioritized roadmap** — a single cross-area action list ordered by impact,
   not by area.

### Step 5: Prioritize across areas

Rank fixes by impact, not by which skill found them. Apply this order:

1. **Indexation blockers first** — anything stopping pages from being crawled or
   indexed (robots `Disallow: /`, sitewide noindex, sitemap full of dead URLs,
   broken canonicals) outranks on-page polish.
2. **Sitewide/template issues over one-off issues** — a bug in one template
   affecting 500 pages beats a single page's long title.
3. **High-traffic, high-intent pages first** within a given fix.
4. Group related findings across skills (e.g., the same `http→https` migration
   surfaces in sitemap, redirect, internal-link, canonical, and mixed-content
   audits — present it once as a single root-cause fix).

## Optional: export the report as a Word document or CSV

If the user wants the findings as a `.docx` (for example, to share with stakeholders or attach to a ticket), save the Markdown report to a file and convert it:

```bash
python3 scripts/md_to_docx.py report.md --output report.docx
```

`scripts/md_to_docx.py` uses only the Python standard library (no `pip install`) and renders headings, tables, lists, links, bold/italic, and code blocks. Offer this whenever a user asks for a Word doc, a `.docx`, or a shareable/downloadable report.

To hand the findings back as a spreadsheet instead, flatten the audit JSON to a CSV — one row per ranked check, with its severity:

```bash
python3 scripts/findings_to_csv.py consolidated_report.json --output findings.csv
```

`scripts/findings_to_csv.py` is standard-library only too. Offer it whenever a user asks for a CSV, a spreadsheet, or the full list of findings.

## Resources

- `scripts/md_to_docx.py` — convert the Markdown report into a Word (.docx) document (standard library only)
- `scripts/findings_to_csv.py` — flatten the audit report JSON into a flat findings.csv (standard library only)
- `references/report-template.md` — consolidated report structure
- `references/coverage-map.md` — what each sub-skill covers and what it needs
- `scripts/consolidate_reports.py` — merge per-skill audit reports into one ranked report
