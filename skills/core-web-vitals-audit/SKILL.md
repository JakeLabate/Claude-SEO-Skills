---
name: core-web-vitals-audit
description: Audit a website's Core Web Vitals and page-experience signals (LCP, CLS, INP, TTFB). Optionally pulls real field data from Google PageSpeed Insights (CrUX) and always collects browserless lab proxies — render-blocking CSS/JS, page weight, image dimension and lazy-loading hygiene, TTFB, text compression, DOM size, request counts, and third-party origins. Use when the user asks to audit, analyze, check, or improve Core Web Vitals, page speed, performance, LCP, CLS, INP, page experience, or loading speed of a website.
---

# Core Web Vitals Audit

Audit the Core Web Vitals and page-experience signals of a website and produce an actionable report.

## When to use this skill

Use this skill when the user asks to:

- Audit or improve Core Web Vitals, page speed, or page experience
- Diagnose poor LCP (Largest Contentful Paint), CLS (Cumulative Layout Shift), or INP (Interaction to Next Paint)
- Find render-blocking resources, oversized pages, slow TTFB, or layout-shift causes
- Check that images have dimensions and that the hero/LCP image is not lazy-loaded
- Pull real-world field performance data from Google PageSpeed Insights / CrUX

## How this skill measures

Core Web Vitals are ultimately a **field** metric (real users, measured in CrUX). This skill collects two complementary layers:

1. **Lab proxies (always, no browser required):** static signals that strongly correlate with the vitals — measured TTFB, page weight, render-blocking CSS/JS, image dimension/lazy-loading hygiene, DOM size, request counts, third-party origins, text compression, and resource hints. Fast and dependency-free, but an approximation.
2. **PSI field + lab (optional, `--psi`):** real CrUX field metrics (LCP, CLS, INP, FCP, TTFB) plus a Lighthouse lab score from Google PageSpeed Insights. This is the authoritative source; use it when you need real numbers and have network access.

When PSI data is present, treat it as the verdict ("is this page passing?") and use the lab proxies to explain **why** and what to fix.

## Inputs to collect

Before starting, confirm with the user:

1. **Site URL or URL set** — a live site root URL, a sitemap (`--sitemap`), or a URL list (`--url-list`). Pick representative templates (home, a product/article, a category) rather than the whole site.
2. **Scope** — max pages (default 50; collection is heavier than a text crawl because it fetches subresources).
3. **PSI** — whether to fetch PageSpeed Insights field data (`--psi`), the strategy (`mobile` default, or `desktop`), and an optional API key (`--psi-key`) to raise rate limits.
4. **Budgets** — optional overrides for total page weight, TTFB, JS/CSS size, and DOM node count.

## Workflow

### Step 1: Collect the signals

Use `scripts/collect_vitals.py`:

```bash
python3 scripts/collect_vitals.py https://example.com --max-pages 50 --output vitals_inventory.json
```

Add real field data from PageSpeed Insights (recommended when available):

```bash
python3 scripts/collect_vitals.py https://example.com --psi --psi-strategy mobile --psi-key YOUR_KEY --output vitals_inventory.json
```

The inventory records, per page: measured TTFB and total fetch time, HTML size and compression, render-blocking CSS/JS counts, total/inline scripts, image dimension and lazy-loading hygiene, whether the first (likely LCP) image is lazy-loaded, approximate DOM node count, resource hints, third-party origins, a weight breakdown (CSS/JS/image/total bytes and request count), and the PSI block when enabled.

### Step 2: Run the audit checks

Use `scripts/audit_vitals.py`:

```bash
python3 scripts/audit_vitals.py vitals_inventory.json --output audit_report.json
```

Override budgets if needed, e.g. `--weight-budget 2000000 --ttfb-budget 600 --dom-budget 1400`.

### Step 3: Evaluate the audit checks

Evaluate each check defined in `references/audit-checks.md`. The core checks are:

| Check | Vital | Severity |
|---|---|---|
| PSI field LCP poor (SLOW/AVERAGE) | LCP | High / Medium |
| PSI field CLS poor | CLS | High / Medium |
| PSI field INP poor | INP | High / Medium |
| PSI Lighthouse score < 50 / < 90 | Overall | High / Medium |
| No text compression (gzip/br) | LCP/TTFB | High |
| LCP image is lazy-loaded | LCP | High |
| Slow TTFB (> budget) | LCP/INP | High / Medium |
| Excessive DOM size | INP/CLS | High / Medium |
| Page weight over budget | LCP | Medium |
| Render-blocking JS in head | LCP/INP | Medium |
| Render-blocking CSS (> 2 files) | LCP | Medium |
| Images missing width/height | CLS | Medium |
| Too many requests (> 80) | LCP | Medium |
| Large JS payload (> budget) | INP | Medium |
| Missing viewport meta | — | Medium |
| Missing preconnect for third parties | LCP | Low |
| Large CSS payload | LCP | Low |
| No lazy-loading on image-heavy page | LCP | Low |

### Step 4: Produce the report

Write a report following the structure in `references/report-template.md`:

1. **Summary** — pages analyzed, whether PSI field data was used, median page weight, issue counts by severity
2. **Field vitals** (if PSI used) — per page: LCP / CLS / INP with pass/fail
3. **Issues** — one section per failing check, mapped to the vital it affects, with the page, the measurement, and the fix
4. **Prioritized action list** — ordered by severity and by which vital is failing in the field

### Step 5: Recommend fixes

Map every fix to the vital it improves and quantify where possible:

- **LCP:** preload the hero image, never lazy-load it, add `fetchpriority="high"`; enable text compression; cut render-blocking CSS/JS (inline critical CSS, `defer`/`async` scripts); reduce TTFB (caching/CDN); compress and right-size the LCP image.
- **CLS:** add `width`/`height` (or `aspect-ratio`) to every image and embed; reserve space for ads/embeds; preload fonts and use `font-display: optional/swap`.
- **INP:** reduce and split long JavaScript tasks; remove unused JS; defer non-critical third-party scripts; shrink an oversized DOM.
- Base every recommendation on the measured data (e.g., "your LCP image `/hero.jpg` has `loading="lazy"` — remove it"); never invent metrics. If PSI field data is unavailable for a URL (low traffic), say so and lean on the lab proxies.

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
- `references/audit-checks.md` — full definitions, thresholds, vital mapping, and rationale for every check
- `references/report-template.md` — report output structure
- `scripts/collect_vitals.py` — collect lab proxies (and optional PSI field/lab data) for a set of pages
- `scripts/audit_vitals.py` — run audit checks against a vitals inventory JSON file
