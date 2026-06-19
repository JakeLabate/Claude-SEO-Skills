---
name: site-architecture-audit
description: Audit a website's architecture and crawlability for SEO. Crawls the site and inspects robots.txt and XML sitemaps to find hostname/protocol duplication, URL structure problems, excessive crawl depth, weak directory taxonomy, blocked or conflicting crawl and index directives, and sitemap-to-crawl parity gaps. Use when the user asks to audit, analyze, or improve site architecture, site structure, URL structure, crawlability, indexability, robots.txt, XML sitemaps, canonicalization, or how a site is organized.
---

# Site Architecture Audit

Audit the structural layer of a website (URL design, hostname and protocol canonicalization, robots.txt, XML sitemaps, crawl and index directives, depth distribution, and directory taxonomy) and produce an actionable SEO report.

## When to use this skill

Use this skill when the user asks to:

- Audit or analyze a site's architecture, structure, or how it is organized
- Review URL structure quality (depth, readability, parameters, trailing slashes, case)
- Check crawlability and indexability: robots.txt, meta robots, canonical signals, conflicts between them
- Validate XML sitemaps and how well they match what is actually crawlable
- Confirm hostname and protocol canonicalization (http vs https, www vs non-www)
- Understand click-depth distribution and directory grouping across the site

This skill covers the structural layer. For the link-by-link view of broken links, orphan pages, anchor text, and redirect chains, use `internal-link-audit`. For outbound links use `external-link-audit`. The two are complementary: architecture explains the shape of the site, internal-link explains the flow of equity within it.

## Inputs to collect

Before starting, confirm with the user:

1. **Site URL** : a live site root URL (e.g., `https://example.com`). A live crawl is required because robots.txt, sitemaps, and redirect behavior cannot be assessed from local files alone.
2. **Scope** : full site or a specific section (e.g., `/blog/`).
3. **Crawl limits** : max pages (default 500) and max depth (default 10) for the crawl.
4. **Business context** : site type (e-commerce, blog, local business, SaaS) and the few page templates that matter most, so depth and taxonomy expectations can be set.

## Workflow

### Step 1: Crawl the site and gather architecture signals

Use `scripts/crawl_architecture.py` to crawl from the homepage (same registrable host only), probe the four hostname/protocol variants, fetch and parse robots.txt, and collect every XML sitemap URL (following sitemap index files):

```bash
python3 scripts/crawl_architecture.py https://example.com --max-pages 500 --max-depth 10 --output architecture_inventory.json
```

For every crawled page the inventory records: requested URL, final URL, HTTP status, redirect chain, click depth, scheme, host, path, query, path-segment count, canonical, meta robots, title, and the raw resolved internal link targets (used to detect URL-form inconsistency). It also records the host-variant probe, the parsed robots.txt rules and `Sitemap:` directives, and the full sitemap URL set.

### Step 2: Run the audit checks

Use `scripts/audit_architecture.py` to evaluate every check against the inventory:

```bash
python3 scripts/audit_architecture.py architecture_inventory.json --output audit_report.json
```

Useful flags: `--max-url-depth 4` (path-segment threshold), `--max-click-depth 3` (click-depth threshold), and `--tracking-params utm_source,utm_medium,gclid,fbclid` to extend the tracking-parameter list.

### Step 3: Evaluate the audit checks

Evaluate each check defined in `references/audit-checks.md`. The core checks are:

| Check | Severity |
|---|---|
| Multiple indexable hostname/protocol variants (no canonical host enforcement) | High |
| Important pages blocked by robots.txt | High |
| Conflicting crawl/index directives (disallow + noindex, noindex + canonical elsewhere, canonical to non-200/redirect/noindex) | High |
| Sitemap lists non-indexable URLs (non-200, redirected, noindexed, or non-canonical) | High |
| Indexable pages missing from the XML sitemap (sitemap/crawl parity gap) | Medium |
| Excessive click depth or top-heavy depth distribution | Medium |
| URL structure problems (uppercase, underscores, spaces/encoding, over-long, over-deep, ID-only slugs) | Medium |
| Inconsistent URL forms in internal links (mixed trailing slash, mixed http/https, mixed www) | Medium |
| Crawlable parameter URLs (tracking, session, sort/filter) creating duplicate spaces | Medium |
| Missing or non-200 robots.txt | Medium |
| No XML sitemap found | Medium |
| Pages missing a self-referencing canonical | Low |
| Sitemap not referenced in robots.txt | Low |
| Thin or inconsistent directory taxonomy | Low |
| Sitemap over size limits (50,000 URLs / 50 MB) without a sitemap index | Low |

### Step 4: Produce the report

Write a report following the structure in `references/report-template.md`:

1. **Summary** : pages crawled, canonical host, sitemap/robots status, issue counts by severity
2. **Canonicalization and crawl controls** : host-variant table, robots.txt findings, index-signal conflicts
3. **URL and depth structure** : depth histogram, URL-quality issues, directory map
4. **Sitemap health** : parity gaps and non-indexable entries
5. **Prioritized action list** : ordered by severity and estimated impact

### Step 5: Recommend fixes

For each issue, give a concrete, copy-pasteable recommendation, e.g.:

- Redirect `http://example.com` and `https://www.example.com` to `https://example.com` with a single 301 so only one host variant resolves
- Remove `Disallow: /blog` from robots.txt; it is blocking 42 linked, indexable articles
- Drop `noindex` from `/services/seo` or remove it from the sitemap; the two signals contradict each other
- Lowercase and de-underscore `/Services/SEO_Audit` to `/services/seo-audit` and 301 the old URL
- Add the 60 indexable pages listed below to `sitemap.xml` and reference the sitemap from robots.txt

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
- `references/audit-checks.md` : full definitions, thresholds, and rationale for every audit check
- `references/report-template.md` : report output structure
- `scripts/crawl_architecture.py` : crawl the site, probe host variants, parse robots.txt and sitemaps, build the inventory
- `scripts/audit_architecture.py` : run audit checks against an architecture inventory JSON file
