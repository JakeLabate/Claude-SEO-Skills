---
name: schema-markup-audit
description: Audit a website's structured data (schema markup) for SEO. Extracts JSON-LD, Microdata, and RDFa from pages, validates it against schema.org and Google rich result requirements, and finds missing, invalid, or incomplete markup. Use when the user asks to audit, validate, fix, or improve schema markup, structured data, JSON-LD, or rich result eligibility of a website.
---

# Schema Markup Audit

Audit the structured data (schema markup) of a website and produce an actionable SEO report.

## When to use this skill

Use this skill when the user asks to:

- Audit or validate schema markup / structured data on a website
- Check rich result eligibility (e.g., Product, Article, FAQ, Review snippets)
- Find missing, invalid, or incomplete JSON-LD, Microdata, or RDFa
- Recommend which schema types to add to which pages
- Fix errors or warnings reported by Google's Rich Results Test or Search Console

## Inputs to collect

Before starting, confirm with the user:

1. **Site URL or local files** — a live site root URL (e.g., `https://example.com`), a sitemap URL, a list of URLs, or a local folder of HTML files.
2. **Scope** — full site, a specific section (e.g., `/products/`), or a list of URLs.
3. **Crawl limits** — max pages (default 200) for live crawls.
4. **Business context** — site type (e-commerce, blog, local business, SaaS, etc.) so page-type-to-schema-type expectations can be set.

## Workflow

### Step 1: Gather the page set

- If a sitemap is available (`/sitemap.xml`), fetch it to get the canonical page list.
- Otherwise, crawl from the homepage following only same-host links.
- For local HTML folders, enumerate all `.html` files.

### Step 2: Extract structured data

Use `scripts/extract_schema.py` to fetch pages and extract all structured data (JSON-LD, Microdata, RDFa) into a JSON inventory:

```bash
python3 scripts/extract_schema.py https://example.com --max-pages 200 --output schema_inventory.json
```

For every page, record:

- Each structured data block: format (`json-ld`, `microdata`, `rdfa`), `@type`, raw parsed object
- JSON parse errors in `<script type="application/ld+json">` blocks
- Page metadata: title, canonical URL, meta robots

### Step 3: Run the audit checks

Use `scripts/validate_schema.py` to validate the inventory:

```bash
python3 scripts/validate_schema.py schema_inventory.json --output audit_report.json
```

Evaluate each check defined in `references/audit-checks.md`. The core checks are:

| Check | Severity |
|---|---|
| Invalid JSON-LD (parse errors) | High |
| Missing required properties for the declared type | High |
| Missing schema on key page types (e.g., Product pages without Product schema) | High |
| Missing recommended properties for rich results | Medium |
| Schema/content mismatch (markup describes content not on the page) | Medium |
| Conflicting or duplicate schema blocks on one page | Medium |
| Deprecated types or properties (e.g., `HowTo` rich results retired) | Medium |
| Missing `Organization` / `WebSite` schema on the homepage | Medium |
| Mixed formats for the same entity (JSON-LD + Microdata duplicates) | Low |
| Missing optional enhancements (`sameAs`, `BreadcrumbList`, etc.) | Low |

### Step 4: Verify against external validators

When the site is live, recommend the user confirm key templates with:

- Google Rich Results Test (`https://search.google.com/test/rich-results`)
- Schema.org validator (`https://validator.schema.org/`)

Validate one representative URL per page template rather than every page.

### Step 5: Produce the report

Write a report following the structure in `references/report-template.md`:

1. **Summary** — pages scanned, schema blocks found, types in use, issue counts by severity
2. **Coverage map** — page types vs. expected schema types, showing gaps
3. **Issues** — one section per failing check, listing affected page, schema type, property, and a specific fix
4. **Opportunities** — schema types worth adding for rich result eligibility
5. **Prioritized action list** — ordered by severity and estimated impact

### Step 6: Recommend fixes

For each issue, give a concrete, copy-pasteable recommendation, e.g.:

- Fix the JSON syntax error in the JSON-LD block on `/products/widget` (trailing comma at line 14)
- Add the required `offers` property to the `Product` schema on all product pages, including `price`, `priceCurrency`, and `availability`
- Provide a complete corrected JSON-LD snippet for the page template, using real values from the page content

Always recommend JSON-LD as the implementation format (Google's preferred format) when adding new markup.

## Resources

- `references/audit-checks.md` — full definitions, severities, and rationale for every audit check, plus required/recommended properties per schema type
- `references/report-template.md` — report output structure
- `scripts/extract_schema.py` — crawl pages and extract all structured data into a JSON inventory
- `scripts/validate_schema.py` — run audit checks against a schema inventory JSON file
