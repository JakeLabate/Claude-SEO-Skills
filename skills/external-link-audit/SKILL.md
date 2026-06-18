---
name: external-link-audit
description: Audit a website's external (outbound) links for SEO. Crawls pages to find broken external links, redirected targets, insecure HTTP links, missing rel attributes on affiliate or sponsored links, unsafe target="_blank" usage, and risky or low-quality link destinations. Use when the user asks to audit, analyze, check, or clean up external links, outbound links, broken links to other sites, or affiliate link compliance.
---

# External Link Audit

Audit the external (outbound) links of a website and produce an actionable SEO report.

## When to use this skill

Use this skill when the user asks to:

- Audit or analyze external/outbound links on a website
- Find broken external links (link rot) or redirected destinations
- Check affiliate, sponsored, or paid links for correct `rel` attribution
- Find insecure `http://` outbound links or unsafe `target="_blank"` usage
- Review which external domains a site links to and how often

## Inputs to collect

Before starting, confirm with the user:

1. **Site URL or local files** — a live site root URL (e.g., `https://example.com`), a sitemap URL, or a local folder of HTML files.
2. **Scope** — full site, a specific section (e.g., `/blog/`), or a list of URLs.
3. **Crawl limits** — max pages (default 500) and max depth (default 5) for live crawls.
4. **Known paid/affiliate domains** — domains that must carry `rel="sponsored"` (e.g., `amzn.to`, affiliate networks), if any.

## Workflow

### Step 1: Gather the page set and extract external links

- If a sitemap is available (`/sitemap.xml`), fetch it to get the canonical page list.
- Otherwise, crawl from the homepage following only same-host links.
- For local HTML folders, enumerate all `.html` files.

Use `scripts/extract_external_links.py` to crawl the site and collect every external link into a JSON inventory:

```bash
python3 scripts/extract_external_links.py https://example.com --max-pages 500 --max-depth 5 --output external_links.json
```

For every external link, the inventory records: source page, target URL, target domain, anchor text, `rel` attributes, `target` attribute, and whether the link is in `<nav>`/`<footer>` or in main content.

### Step 2: Check link targets and run the audit

Use `scripts/check_external_links.py` to resolve the HTTP status of each external target (deduplicated per URL) and run all audit checks:

```bash
python3 scripts/check_external_links.py external_links.json --output audit_report.json
```

Add `--sponsored-domains amzn.to,partner.example` to flag affiliate domains missing `rel="sponsored"`. Add `--skip-status-checks` to run only the static checks without network requests.

### Step 3: Evaluate the audit checks

Evaluate each check defined in `references/audit-checks.md`. The core checks are:

| Check | Severity |
|---|---|
| Broken external links (4xx/5xx or unresolvable targets) | High |
| Affiliate/paid links missing `rel="sponsored"` | High |
| Insecure `http://` external links | Medium |
| Redirected external links (3xx targets) | Medium |
| `target="_blank"` without `rel="noopener"`/`noreferrer` | Medium |
| User-generated content links missing `rel="ugc"`/`nofollow` | Medium |
| Generic anchor text on external links | Low |
| Excessive external links on a page (> 100) | Low |
| Sitewide (nav/footer) external links | Low |

### Step 4: Produce the report

Write a report following the structure in `references/report-template.md`:

1. **Summary** — pages crawled, external links found, unique domains, issue counts by severity
2. **Domain overview** — most-linked external domains with link counts and follow/nofollow split
3. **Issues** — one section per failing check, listing source page, target URL, anchor text, and a specific fix
4. **Prioritized action list** — ordered by severity and estimated impact

### Step 5: Recommend fixes

For each issue, give a concrete, copy-pasteable recommendation, e.g.:

- Remove or replace the dead link `https://gone.example/page` on `/blog/post-1`; link to an archived copy or an equivalent live resource
- Update `http://partner.example` on `/resources` to `https://partner.example`
- Add `rel="sponsored"` to the affiliate link `https://amzn.to/xyz` on `/reviews/widget`
- Add `rel="noopener"` to the `target="_blank"` link on `/about`

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
- `scripts/extract_external_links.py` — crawl a site and build the external link inventory
- `scripts/check_external_links.py` — resolve target statuses and run audit checks
