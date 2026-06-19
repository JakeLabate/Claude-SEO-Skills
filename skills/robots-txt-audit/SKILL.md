---
name: robots-txt-audit
description: Audit a website's robots.txt for SEO. Fetches and parses robots.txt to find a redirected or HTML-served file, a 5xx that Google reads as "block everything", a sitewide Disallow: / that blocks the whole site, syntax errors and directives before any User-agent, CSS/JS resources blocked from rendering, missing or unreachable Sitemap: directives, a missing default User-agent: * group, unsupported directives (noindex, nofollow, crawl-delay) that Google ignores, files over the 500 KiB limit, BOM/encoding issues, and duplicate or empty rules. Use when the user asks to audit, analyze, check, validate, debug, or fix a robots.txt file, crawl directives, or what search engines are allowed to crawl.
---

# Robots.txt Audit

Audit a website's robots.txt file and produce an actionable SEO report.

## When to use this skill

Use this skill when the user asks to:

- Audit, validate, or check a robots.txt file or crawl directives
- Find out why pages are not being crawled or why Google says a URL is "blocked by robots.txt"
- Check that important pages aren't blocked and that CSS/JS resources can be rendered
- Confirm robots.txt declares the XML sitemap and returns 200 as plain text
- Catch a stray `Disallow: /` that took the whole site out of search
- Clean up syntax errors and unsupported directives (`noindex`, `crawl-delay`, etc.)

## Inputs to collect

Before starting, confirm with the user:

1. **Site URL or robots.txt URL** — a live site root (e.g., `https://example.com`, which fetches `/robots.txt`) or a specific robots.txt URL (`--robots`).
2. **Resource check** — whether to fetch the homepage and test its CSS/JS/image references against the rules (default on). Use `--no-resources` to skip it.

> **What robots.txt does and does not do:** robots.txt controls *crawling*, not *indexing*. A `Disallow` stops compliant crawlers from fetching a page, but a blocked URL can still be indexed (without a snippet) if other pages link to it. To keep a page out of the index, allow crawling and use a `noindex` meta tag or `X-Robots-Tag` header instead — `noindex` inside robots.txt is unsupported and ignored. Most checks here protect crawl access and rendering rather than indexing.

## Workflow

### Step 1: Fetch and parse robots.txt

Use `scripts/collect_robots.py`:

```bash
python3 scripts/collect_robots.py https://example.com --output robots_inventory.json
```

Point directly at a robots.txt with `--robots`:

```bash
python3 scripts/collect_robots.py https://example.com/robots.txt --robots --output robots_inventory.json
```

The script fetches `/robots.txt` without auto-following redirects (so a redirected or HTML-served file is visible), records HTTP status, content type, byte size, gzip, and a BOM flag, then parses user-agent groups, `Sitemap:` directives, comments, unknown/unsupported directives, and per-line syntax errors. It probes every declared sitemap URL for status and (unless `--no-resources`) fetches the homepage to test same-host CSS/JS/image references against the `*` group's rules.

### Step 2: Run the audit checks

Use `scripts/audit_robots.py`:

```bash
python3 scripts/audit_robots.py robots_inventory.json --output audit_report.json
```

### Step 3: Evaluate the audit checks

Evaluate each check defined in `references/audit-checks.md`. The core checks are:

| Check | Severity |
|---|---|
| robots.txt returns 5xx (read as "block everything") | High |
| robots.txt redirects instead of returning the file | High |
| robots.txt served as HTML, not plain text | High |
| Sitewide `Disallow: /` blocks the whole site | High |
| Syntax error / directive before any User-agent | High |
| File exceeds 500 KiB | High |
| Render-critical CSS/JS blocked from crawling | Medium |
| No `Sitemap:` directive | Medium |
| Declared `Sitemap:` URL unreachable or not absolute | Medium |
| No default `User-agent: *` group | Medium |
| Unsupported directive (noindex, nofollow, crawl-delay) | Medium |
| robots.txt missing entirely (404) | Low |
| Duplicate `User-agent: *` group | Low |
| UTF-8 BOM precedes the file | Low |
| Empty `Disallow:` alongside real rules | Low |

### Step 4: Produce the report

Write a report following the structure in `references/report-template.md`:

1. **Summary** — fetch status, group count, sitemaps declared, issue counts by severity
2. **Fetch & file** — status, content type, size, redirect/HTML/BOM flags
3. **Issues** — one section per failing check, with the offending directive/line and the fix
4. **Prioritized action list** — ordered by severity and impact

### Step 5: Recommend fixes

For each issue, give a concrete fix:

- **5xx / redirect / HTML:** serve robots.txt from the root path as `text/plain` returning `200` directly (no redirect, no HTML error page). A persistent 5xx will pause crawling site-wide.
- **Sitewide `Disallow: /`:** confirm it is intentional (it usually is not on a production site) and remove or scope it; this single line can deindex an entire domain.
- **Syntax errors:** fix malformed lines — every directive needs `field: value`, and `Disallow`/`Allow` must follow a `User-agent` line.
- **Blocked resources:** add `Allow:` rules (or remove the `Disallow`) so Googlebot can fetch the CSS/JS it needs to render the page.
- **Sitemap directive:** add an absolute `Sitemap:` line for each sitemap (or the index); fix any that 404.
- **Unsupported directives:** remove `noindex`/`nofollow` from robots.txt and enforce them via meta robots or `X-Robots-Tag`; drop `crawl-delay` (Google ignores it — set the rate in Search Console if needed).
- Base every recommendation on the observed file; quote the exact line to change and do not invent rules.

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
- `references/audit-checks.md` — full definitions, thresholds, and rationale for every audit check
- `references/report-template.md` — report output structure
- `scripts/collect_robots.py` — fetch, parse, and probe a site's robots.txt
- `scripts/audit_robots.py` — run audit checks against a robots.txt inventory JSON file
