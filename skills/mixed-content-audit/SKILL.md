---
name: mixed-content-audit
description: Audit an HTTPS website for mixed content and insecure resources. Crawls pages and inspects every subresource to find active mixed content (http scripts, stylesheets, iframes, objects browsers block on https pages), insecure form actions that submit over http, passive mixed content (http images, audio, video), legacy protocol-relative (//) resource URLs, and pages still served over http. Use when the user asks to audit, check, or fix mixed content, insecure resources, the padlock / not-secure warning, an incomplete HTTPS migration, or http resources on an https site.
---

# Mixed Content / HTTPS Audit

Audit an HTTPS site for insecure (`http://`) resources and produce an actionable
report. Mixed content breaks pages and strips the padlock; this skill finds every
instance and groups it by root cause.

## When to use this skill

Use this skill when the user asks to:

- Audit or fix mixed content / the browser "Not secure" warning
- Find `http://` scripts, styles, iframes, images, or media on `https://` pages
- Verify an HTTPS migration is complete
- Find insecure form actions

## Inputs to collect

1. **Site URL or URL list** — a live `https://` site root to crawl (auto-seeds
   from `/sitemap.xml`), or a text file with `--url-list`.
2. **Scope** — pages to crawl (default 500, `--max-pages`).

## Workflow

### Step 1: Crawl and inventory subresources

Use `scripts/extract_resources.py`:

```bash
python3 scripts/extract_resources.py https://example.com --max-pages 500 --output resource_inventory.json
# already crawled once (e.g. in a full SEO audit)? skip the crawl and reuse the shared cache:
# python3 scripts/fetch_pages.py https://example.com --output page_cache.json
# python3 scripts/extract_resources.py --from-cache page_cache.json --output resource_inventory.json
```

For every page it records each subresource (scripts, stylesheets, images,
iframes, media, embeds, form actions) with its tag, attribute, resolved URL, and
scheme.

### Step 2: Run the audit checks

```bash
python3 scripts/audit_resources.py resource_inventory.json --output audit_report.json
```

### Step 3: Evaluate the audit checks

Evaluate each check in `references/audit-checks.md`. Core checks:

| Check | Severity |
|---|---|
| Active mixed content (script/style/iframe/object over http) | High |
| Insecure form action (http) | High |
| Passive mixed content (img/audio/video over http) | Medium |
| Protocol-relative (`//`) resource | Low |
| Page served over http | Info |

### Step 4: Produce the report

Write a report following `references/report-template.md`: summary by severity,
active mixed content and insecure forms first, then passive, grouped by the host
serving the insecure resource, and a prioritized action list.

### Step 5: Recommend fixes

- **Active/passive mixed content:** load the resource over `https://` (most hosts
  already support it — just change the scheme), self-host it, or remove it.
- **Insecure form action:** change the `action` to `https://`.
- **Protocol-relative URLs:** make them explicit `https://`.
- **Insecure pages:** fix the site-wide HTTPS redirect at the source (cross-check
  the `redirect-audit` skill).
- Group fixes by host — one insecure CDN usually explains many rows.
- Base every recommendation on the crawled inventory; never invent URLs.

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
- `references/audit-checks.md` — full definitions and rationale
- `references/report-template.md` — report output structure
- `scripts/extract_resources.py` — crawl and inventory subresources
- `scripts/audit_resources.py` — run mixed-content audit checks
