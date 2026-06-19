---
name: open-graph-audit
description: Audit a website's Open Graph and Twitter Card (social sharing) metadata for SEO and link previews. Crawls pages and probes each share image to find missing og:title, og:description, og:image, or og:url; broken or non-image or relative og:image URLs; og:url that mismatches the canonical; missing twitter:card; over-length social titles/descriptions; and brand-default images reused across many pages. Use when the user asks to audit, check, validate, or fix Open Graph tags, og: tags, Twitter Cards, social sharing previews, social metadata, or link preview images on a website.
---

# Open Graph / Social Metadata Audit

Audit a website's Open Graph and Twitter Card tags and produce an actionable
report on how the site's links render when shared.

## When to use this skill

Use this skill when the user asks to:

- Audit, validate, or check Open Graph (`og:*`) or Twitter Card (`twitter:*`) tags
- Diagnose why links look wrong / have no image when shared on social or chat
- Find missing or broken share images, or `og:url` that points at the wrong URL
- Improve social click-through and link previews

## Inputs to collect

1. **Site URL or URL list** — a live site root to crawl (auto-seeds from
   `/sitemap.xml`), or a text file with `--url-list`.
2. **Scope** — pages to crawl (default 500, `--max-pages`).
3. **Image probing** — whether to probe each `og:image`/`twitter:image` for
   status and content type (default on; `--no-probe` to skip).

## Workflow

### Step 1: Crawl and probe social tags

Use `scripts/extract_social.py`:

```bash
python3 scripts/extract_social.py https://example.com --max-pages 500 --output social_inventory.json
# already crawled once (e.g. in a full SEO audit)? skip the crawl and reuse the shared cache:
# python3 scripts/fetch_pages.py https://example.com --output page_cache.json
# python3 scripts/extract_social.py --from-cache page_cache.json --output social_inventory.json
```

It records each page's OG and Twitter Card tags, canonical, and meta robots, then
probes each unique share image for HTTP status and content type.

### Step 2: Run the audit checks

```bash
python3 scripts/audit_social.py social_inventory.json --output audit_report.json
```

### Step 3: Evaluate the audit checks

Evaluate each check in `references/audit-checks.md`. Core checks:

| Check | Severity |
|---|---|
| Missing og:title | High |
| Missing og:image | High |
| Broken og:image (non-200) | High |
| Missing og:description | Medium |
| Missing og:url | Medium |
| og:url mismatches canonical | Medium |
| og:image not an image / relative | Medium |
| Missing twitter:card (no OG fallback) | Low |
| og:title / og:description too long | Low |
| Duplicate/default share image across many pages | Info |

### Step 4: Produce the report

Write a report following `references/report-template.md`: summary by severity,
broken/missing images first, then completeness gaps, then a prioritized action
list.

### Step 5: Recommend fixes

- **Missing/broken image:** add or repair an absolute `https://` `og:image`
  (1200×630 recommended) that returns `200`.
- **Missing og:title/description:** add them (page title and meta description are
  good sources).
- **og:url missing/mismatched:** set it to the canonical absolute URL.
- **Relative/non-image og:image:** use an absolute URL to a real image file.
- **twitter:card:** add `summary_large_image` for most content.
- Base every recommendation on observed data; never assume an image loads.

## Optional: export the report as a Word document

If the user wants the findings as a `.docx` (for example, to share with stakeholders or attach to a ticket), save the Markdown report to a file and convert it:

```bash
python3 scripts/md_to_docx.py report.md --output report.docx
```

`scripts/md_to_docx.py` uses only the Python standard library (no `pip install`) and renders headings, tables, lists, links, bold/italic, and code blocks. Offer this whenever a user asks for a Word doc, a `.docx`, or a shareable/downloadable report.

## Resources

- `scripts/md_to_docx.py` — convert the Markdown report into a Word (.docx) document (standard library only)
- `references/audit-checks.md` — full definitions, thresholds, and rationale
- `references/report-template.md` — report output structure
- `scripts/extract_social.py` — crawl pages and probe share images
- `scripts/audit_social.py` — run audit checks against the inventory
