---
name: meta-data-audit
description: Audit a website's title tags and meta descriptions for SEO. Crawls pages to find missing, duplicate, too-long, too-short, or multiple title tags and meta descriptions, generic or boilerplate titles, and metadata that wastes the snippet. Use when the user asks to audit, analyze, check, or improve page titles, title tags, meta descriptions, metadata, or SERP snippets of a website.
---

# Meta Data Audit

Audit the title tags and meta descriptions of a website and produce an actionable SEO report.

## When to use this skill

Use this skill when the user asks to:

- Audit or analyze title tags and meta descriptions on a website
- Find pages with missing, duplicate, or multiple titles or meta descriptions
- Find titles or descriptions that are too long (truncated in SERPs) or too short (wasted snippet space)
- Identify generic, boilerplate, or keyword-stuffed metadata
- Improve click-through rates from search by tightening SERP snippets

## Inputs to collect

Before starting, confirm with the user:

1. **Site URL or local files** — a live site root URL (e.g., `https://example.com`), a sitemap URL, a list of URLs, or a local folder of HTML files.
2. **Scope** — full site, a specific section (e.g., `/blog/`), or a list of URLs.
3. **Crawl limits** — max pages (default 500) for live crawls.
4. **Brand suffix** — the brand pattern appended to titles (e.g., `| Acme Co`), if any, so brand-only and duplicate-after-brand titles can be detected accurately.

## Workflow

### Step 1: Gather the page set and extract metadata

- If a sitemap is available (`/sitemap.xml`), fetch it to get the canonical page list.
- Otherwise, crawl from the homepage following only same-host links.
- For local HTML folders, enumerate all `.html` files.

Use `scripts/extract_metadata.py` to fetch pages and collect every title tag and meta description into a JSON inventory:

```bash
python3 scripts/extract_metadata.py https://example.com --max-pages 500 --output metadata_inventory.json
```

For every page, the inventory records: every `<title>` and `<meta name="description">` value (including duplicates), the first `<h1>`, canonical URL, meta robots, and `og:title`/`og:description` for comparison.

### Step 2: Run the audit checks

Use `scripts/audit_metadata.py` to run all audit checks against the inventory:

```bash
python3 scripts/audit_metadata.py metadata_inventory.json --output audit_report.json
```

Add `--brand-suffix "| Acme Co"` to strip the brand pattern before duplicate detection and to flag brand-only titles. Noindexed pages are excluded from duplicate checks by default.

### Step 3: Evaluate the audit checks

Evaluate each check defined in `references/audit-checks.md`. The core checks are:

| Check | Severity |
|---|---|
| Missing or empty title tag | High |
| Missing or empty meta description | High |
| Duplicate titles across pages | High |
| Duplicate meta descriptions across pages | High |
| Multiple title tags or meta descriptions on one page | Medium |
| Title too long (> 60 characters, likely truncated) | Medium |
| Title too short (< 30 characters, wasted space) | Medium |
| Description too long (> 160 characters, likely truncated) | Medium |
| Description too short (< 70 characters, wasted space) | Medium |
| Generic or boilerplate titles ("Home", "Untitled", brand-only) | Medium |
| Description duplicates the title | Low |
| Keyword stuffing in the title | Low |
| Title/H1 mismatch | Informational |

### Step 4: Produce the report

Write a report following the structure in `references/report-template.md`:

1. **Summary** — pages crawled, titles and descriptions found, issue counts by severity
2. **Length distribution** — how titles and descriptions spread across short/good/long bands
3. **Issues** — one section per failing check, listing the page, the current value, and a specific fix
4. **Prioritized action list** — ordered by severity and estimated impact

### Step 5: Recommend fixes

For each issue, give a concrete, copy-pasteable recommendation. When drafting replacement titles and descriptions:

- Keep titles near 60 characters and descriptions near 155 characters
- Lead with the page's primary topic; put the brand suffix last
- Base every value on the visible page content; never invent facts, prices, or claims
- Write descriptions that summarize the page and give searchers a reason to click, without keyword stuffing

Example recommendations:

- Add a title to `/services/seo-audit`: `SEO Audit Services For B2B SaaS | Acme Co`
- Shorten the 87-character title on `/blog/post-1` to lead with the primary topic
- Differentiate the duplicate description shared by `/locations/boston` and `/locations/cambridge` with location-specific copy

## Resources

- `references/audit-checks.md` — full definitions, thresholds, and rationale for every audit check
- `references/report-template.md` — report output structure
- `scripts/extract_metadata.py` — crawl a site and build the title/description inventory
- `scripts/audit_metadata.py` — run audit checks against a metadata inventory JSON file
