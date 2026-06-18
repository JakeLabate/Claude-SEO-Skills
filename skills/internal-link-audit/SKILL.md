---
name: internal-link-audit
description: Audit a website's internal linking structure for SEO. Crawls pages to find broken internal links, orphan pages, redirect chains, deep pages, missing or weak anchor text, and internal link distribution issues. Use when the user asks to audit, analyze, or improve internal links, site structure, link equity, or crawlability of a website.
---

# Internal Link Audit

Audit the internal linking structure of a website and produce an actionable SEO report.

## When to use this skill

Use this skill when the user asks to:

- Audit or analyze internal links on a website
- Find broken internal links or redirect chains
- Identify orphan pages (pages with no internal links pointing to them)
- Review anchor text quality for internal links
- Improve crawl depth, site architecture, or internal link equity distribution

## Inputs to collect

Before starting, confirm with the user:

1. **Site URL or local files** — a live site root URL (e.g., `https://example.com`), a sitemap URL, or a local folder of HTML files.
2. **Scope** — full site, a specific section (e.g., `/blog/`), or a list of URLs.
3. **Crawl limits** — max pages (default 500) and max depth (default 5) for live crawls.

## Workflow

### Step 1: Gather the page set

- If a sitemap is available (`/sitemap.xml`), fetch it to get the canonical page list.
- Otherwise, crawl from the homepage following only same-host links.
- For local HTML folders, enumerate all `.html` files.

Use `scripts/crawl_links.py` to crawl a live site and extract all internal links into a JSON link graph:

```bash
python3 scripts/crawl_links.py https://example.com --max-pages 500 --max-depth 5 --output link_graph.json
```

### Step 2: Build the link graph

For every page, record:

- Outgoing internal links: target URL, anchor text, `rel` attributes (`nofollow`), whether the link is in `<nav>`/`<footer>` or in main content
- HTTP status of each target (200, 3xx, 4xx, 5xx)
- Page metadata: title, canonical URL, meta robots (`noindex`, `nofollow`)

### Step 3: Run the audit checks

Use `scripts/analyze_graph.py` to analyze the link graph:

```bash
python3 scripts/analyze_graph.py link_graph.json --output audit_report.json
```

Evaluate each check defined in `references/audit-checks.md`. The core checks are:

| Check | Severity |
|---|---|
| Broken internal links (4xx/5xx targets) | High |
| Orphan pages (in sitemap but zero inbound internal links) | High |
| Redirect chains and redirected internal links (3xx targets) | Medium |
| Deep pages (click depth > 3 from homepage) | Medium |
| Generic anchor text ("click here", "read more", bare URLs) | Medium |
| Pages with excessive outgoing links (> 150) | Low |
| Nofollow on internal links | Low |
| Links to non-canonical or noindexed URLs | Medium |
| Low inbound link count on important pages | Medium |

### Step 4: Produce the report

Write a report following the structure in `references/report-template.md`:

1. **Summary** — pages crawled, total internal links, issue counts by severity
2. **Issues** — one section per failing check, listing affected source page, target page, anchor text, and a specific fix
3. **Opportunities** — pages that deserve more internal links, suggested anchor text using target page keywords
4. **Prioritized action list** — ordered by severity and estimated impact

### Step 5: Recommend fixes

For each issue, give a concrete, copy-pasteable recommendation, e.g.:

- Replace the broken link `/old-page` on `/blog/post-1` with `/new-page`
- Add 2–3 contextual links to the orphan page `/services/seo-audit` from topically related pages
- Change anchor text "click here" on `/about` to descriptive text containing the target page's primary keyword

## Optional: export the report as a Word document

If the user wants the findings as a `.docx` (for example, to share with stakeholders or attach to a ticket), save the Markdown report to a file and convert it:

```bash
python3 scripts/md_to_docx.py report.md --output report.docx
```

`scripts/md_to_docx.py` uses only the Python standard library (no `pip install`) and renders headings, tables, lists, links, bold/italic, and code blocks. Offer this whenever a user asks for a Word doc, a `.docx`, or a shareable/downloadable report.

## Resources

- `scripts/md_to_docx.py` — convert the Markdown report into a Word (.docx) document (standard library only)
- `references/audit-checks.md` — full definitions, thresholds, and rationale for every audit check
- `references/report-template.md` — report output structure
- `scripts/crawl_links.py` — crawl a site and build the internal link graph
- `scripts/analyze_graph.py` — run audit checks against a link graph JSON file
