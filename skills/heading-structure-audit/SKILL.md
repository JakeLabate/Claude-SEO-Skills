---
name: heading-structure-audit
description: Audit a website's heading structure (H1–H6) for SEO and accessibility. Crawls pages to find missing or multiple H1s, skipped heading levels, empty headings, headings that don't start at H1, overly long headings, and duplicate headings. Use when the user asks to audit, analyze, check, or improve heading tags, the H1, the heading hierarchy, document outline, or content structure of a website.
---

# Heading Structure Audit

Audit the heading hierarchy (H1–H6) of a website and produce an actionable SEO and accessibility report.

## When to use this skill

Use this skill when the user asks to:

- Audit or analyze the heading tags or heading hierarchy of a website
- Find pages with missing, empty, or multiple H1s
- Find broken outlines: skipped heading levels (e.g., H2 jumping to H4) or pages that don't start at H1
- Identify overly long or duplicated headings
- Improve content structure, document outline, or accessibility of headings

## Inputs to collect

Before starting, confirm with the user:

1. **Site URL or local files** — a live site root URL (e.g., `https://example.com`), a sitemap URL, a list of URLs, or a local folder of HTML files.
2. **Scope** — full site, a specific section (e.g., `/blog/`), or a list of URLs.
3. **Crawl limits** — max pages (default 500) for live crawls.
4. **Long-heading threshold** — character count above which a heading is "too long" (default 70).

## Workflow

### Step 1: Gather the page set and extract headings

- If a sitemap is available (`/sitemap.xml`), it is used to get the canonical page list.
- Otherwise, the crawler starts from the homepage following only same-host links.
- For local HTML folders, all `.html` files are enumerated.

Use `scripts/extract_headings.py` to build a heading inventory:

```bash
python3 scripts/extract_headings.py https://example.com --max-pages 500 --output heading_inventory.json
```

For every page the inventory records the `<title>` and the full list of headings in document order, each with its level (1–6) and trimmed text.

### Step 2: Run the audit checks

Use `scripts/audit_headings.py` to run all audit checks against the inventory:

```bash
python3 scripts/audit_headings.py heading_inventory.json --long-heading 70 --output audit_report.json
```

### Step 3: Evaluate the audit checks

Evaluate each check defined in `references/audit-checks.md`. The core checks are:

| Check | Severity |
|---|---|
| Missing H1 | High |
| No headings at all | High |
| Multiple H1s | Medium |
| Skipped heading level (e.g., H2 → H4) | Medium |
| Empty heading element | Medium |
| First heading is not H1 | Low |
| Heading too long (> 70 chars) | Low |
| Duplicate heading text on one page | Low |
| Title / H1 topical mismatch | Informational |

### Step 4: Produce the report

Write a report following the structure in `references/report-template.md`:

1. **Summary** — pages crawled, headings found, issue counts by severity
2. **Issues** — one section per failing check, listing the page, the offending heading(s), and a specific fix
3. **Prioritized action list** — ordered by severity and estimated impact

### Step 5: Recommend fixes

For each issue, give a concrete, copy-pasteable recommendation. When proposing headings:

- Every page should have exactly one H1 that states the page's primary topic
- Headings should form a logical, gap-free outline: H1 → H2 → H3, never skipping a level downward
- Base every suggested heading on the page's actual content; never invent topics the page does not cover
- Reserve heading tags for true section titles — do not wrap styling-only text in headings, and do not demote real section titles to `<div>`s for visual reasons (use CSS instead)

Example recommendations:

- Add an H1 to `/pricing`: `H1: Pricing Plans for Teams of Every Size`
- `/blog/post-1` jumps from H2 to H4 under "Methodology" — change the H4 subsections to H3
- Merge the two H1s on the homepage; demote the tagline H1 to a paragraph and keep the brand-value H1

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
- `scripts/extract_headings.py` — crawl a site and build the heading inventory
- `scripts/audit_headings.py` — run audit checks against a heading inventory JSON file
