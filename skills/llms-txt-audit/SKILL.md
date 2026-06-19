---
name: llms-txt-audit
description: Audit a website's /llms.txt for AI/LLM discoverability. Fetches and parses the llms.txt markdown file (per llmstxt.org) to find a missing file, a file served as HTML instead of markdown, a missing required H1 title, a missing blockquote summary, broken (non-200) or redirecting links, links missing descriptions, malformed list items that aren't proper markdown links, links to the wrong host, links that are noindexed or blocked by robots.txt, relative instead of absolute URLs, duplicate links, an empty file with no sections, the wrong content type, and whether a companion /llms-full.txt exists. Use when the user asks to audit, analyze, check, validate, create, or fix an llms.txt or llms-full.txt file, or to make a site discoverable and usable by AI assistants and LLMs.
---

# llms.txt Audit

Audit a website's `/llms.txt` file and produce an actionable report for AI/LLM discoverability.

## When to use this skill

Use this skill when the user asks to:

- Audit, validate, or check an `llms.txt` or `llms-full.txt` file
- Make a site discoverable and usable by AI assistants, chatbots, and LLMs
- Find broken, redirecting, or blocked links inside `llms.txt`
- Confirm `llms.txt` follows the llmstxt.org structure (H1 title, summary, link sections)
- Decide what should go into `llms.txt` vs. `llms-full.txt`

## Background: what llms.txt is

`llms.txt` is a proposed standard (https://llmstxt.org) for a markdown file at the site root (`/llms.txt`) that gives LLMs a concise, curated map of the site's most useful content. Unlike `robots.txt` (which controls crawling) or `sitemap.xml` (which lists every URL), `llms.txt` is hand-curated and human-readable. Its structure:

```markdown
# Project Name              ← required: the only mandatory element

> A short summary.          ← recommended blockquote summary

Optional free-form markdown with key context (no headings).

## Docs                     ← H2 section of curated links
- [Quickstart](https://example.com/quickstart): How to get started.
- [API reference](https://example.com/api): Full API docs.

## Optional                 ← an "Optional" section may be skipped by LLMs with limited context
- [Changelog](https://example.com/changelog): Release history.
```

A companion `/llms-full.txt` may contain the full expanded content in one file. This skill audits structure and link health against that spec.

## Inputs to collect

Before starting, confirm with the user:

1. **Site URL or llms.txt URL** — a live site root (e.g., `https://example.com`, which fetches `/llms.txt`) or a specific llms.txt URL (`--llms`).
2. **Scope** — how many referenced links to probe (default 300, capped with `--max-urls`).
3. **Probing** — whether to fetch each link to check status/redirect/noindex (default on). Use `--no-probe` for a fast structure-only pass.

## Workflow

### Step 1: Fetch and parse llms.txt

Use `scripts/collect_llms.py`:

```bash
python3 scripts/collect_llms.py https://example.com --max-urls 300 --output llms_inventory.json
```

Point directly at an llms.txt with `--llms`:

```bash
python3 scripts/collect_llms.py https://example.com/llms.txt --llms --output llms_inventory.json
```

The script fetches `/llms.txt` without auto-following redirects (so a redirected or HTML-served file is visible), records status / content type / size, parses the H1 title, blockquote summary, and H2 sections with their list items, then probes every referenced link (status, redirect target, canonical, meta robots, X-Robots-Tag, robots.txt disallow). It also checks whether `/llms-full.txt` exists.

### Step 2: Run the audit checks

Use `scripts/audit_llms.py`:

```bash
python3 scripts/audit_llms.py llms_inventory.json --output audit_report.json
```

### Step 3: Evaluate the audit checks

Evaluate each check defined in `references/audit-checks.md`. The core checks are:

| Check | Severity |
|---|---|
| /llms.txt missing (non-200) | High |
| Served as HTML, not markdown/plain text | High |
| Missing required H1 title | High |
| Referenced link returns 4xx/5xx/error | High |
| /llms.txt itself redirects | Medium |
| Referenced link redirects (not a final 200) | Medium |
| Missing blockquote summary | Medium |
| Link list item missing a description | Medium |
| Malformed list item (not a markdown link) | Medium |
| Link on the wrong host | Medium |
| Linked page is noindex or robots-blocked | Medium |
| Wrong content type | Medium |
| Relative URL instead of absolute | Low |
| No sections / no links | Low |
| Duplicate link | Low |
| /llms-full.txt missing | Low |

### Step 4: Produce the report

Write a report following the structure in `references/report-template.md`:

1. **Summary** — file status, H1, sections, links found/probed, issue counts by severity
2. **File structure** — H1, summary present, section list, llms-full.txt presence
3. **Issues** — one section per failing check, listing the link/item, the problem, and the fix
4. **Prioritized action list** — ordered by severity and impact

### Step 5: Recommend fixes

For each issue, give a concrete fix:

- **Missing file:** create `/llms.txt` with at minimum an H1 title, a one-line `>` summary, and one or more `## ` sections of curated `- [name](url): description` links. Serve it as `text/markdown` or `text/plain` at the root with a `200`.
- **Served as HTML / wrong content type:** serve the raw markdown file, not a rendered page; set `Content-Type: text/markdown` (or `text/plain`).
- **Missing H1:** add a single top-level `# Project Name` heading — it is the only required element.
- **Broken / redirecting / blocked links:** replace each with its final, canonical, indexable `200` URL (or remove it). Links in llms.txt should point straight to the live destination.
- **Missing descriptions / malformed items:** rewrite each item as `- [Descriptive title](absolute-url): one-line description` so an LLM can tell what each link is for.
- **Relative URLs:** use absolute `https://` URLs so the file works when fetched out of context.
- **llms-full.txt:** if the user wants full-content ingestion, generate `/llms-full.txt` with the expanded page contents.
- Base every recommendation on the observed file; quote the exact line to change and do not invent URLs.

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
- `references/audit-checks.md` — full definitions and rationale for every audit check
- `references/report-template.md` — report output structure
- `scripts/collect_llms.py` — fetch, parse, and probe a site's llms.txt
- `scripts/audit_llms.py` — run audit checks against an llms.txt inventory JSON file
