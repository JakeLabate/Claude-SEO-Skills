---
name: redirect-audit
description: Audit a website's redirects for SEO. Resolves the full redirect chain for every URL to find redirect chains and loops, redirects that end in 404s or errors, temporary (302) redirects used for permanent moves, HTTPS-to-HTTP downgrades, client-side meta-refresh and JavaScript redirects, dropped query strings, and canonicals that point at redirecting URLs. Use when the user asks to audit, analyze, check, or fix redirects, redirect chains, 301s, 302s, redirect loops, or HTTP-to-HTTPS migration issues on a website.
---

# Redirect Audit

Resolve and audit the redirects of a website and produce an actionable SEO report.

## When to use this skill

Use this skill when the user asks to:

- Audit or analyze a site's redirects, 301s, 302s, or redirect rules
- Find redirect chains, redirect loops, or redirects that end in 404s/errors
- Verify an HTTP→HTTPS or domain/www migration redirects cleanly in one hop
- Find temporary (302/307) redirects that should be permanent (301/308)
- Detect meta-refresh or JavaScript redirects that should be server-side 301s
- Check that canonical tags and sitemap URLs don't point at redirecting URLs

## Inputs to collect

Before starting, confirm with the user:

1. **Site URL or URL set** — a live site root URL (e.g., `https://example.com`), a sitemap URL (`--sitemap`), or a text file of specific URLs (`--url-list`). Sitemap and URL-list modes are best for verifying a known migration map.
2. **Scope** — full crawl, a sitemap, or an explicit list. For a migration, supply the list of old URLs so each is checked for a clean single hop.
3. **Crawl limits** — max pages (default 500) and max hops to follow (default 10).
4. **Chain tolerance** — the maximum acceptable number of redirect hops before flagging (default 1; every redirect should reach its destination in a single hop).

## Workflow

### Step 1: Resolve redirect chains

Use `scripts/collect_redirects.py` to follow each URL one hop at a time and record the full chain:

```bash
python3 scripts/collect_redirects.py https://example.com --max-pages 500 --output redirect_inventory.json
```

Other input modes:

```bash
python3 scripts/collect_redirects.py https://example.com/sitemap.xml --sitemap --output redirect_inventory.json
python3 scripts/collect_redirects.py old_urls.txt --url-list --output redirect_inventory.json
```

For every URL the inventory records each hop (URL, status code, target), the chain length, the final URL and status, whether the chain loops or exceeds the hop limit, scheme/host changes, HTTPS→HTTP downgrades, dropped query strings, the final page's canonical, and any meta-refresh or JavaScript redirect on the final page.

### Step 2: Run the audit checks

Use `scripts/audit_redirects.py` to evaluate the inventory:

```bash
python3 scripts/audit_redirects.py redirect_inventory.json --output audit_report.json
```

Use `--max-chain 0` to flag *every* redirect (useful when checking that sitemap/canonical URLs are all direct 200s), or a higher number to tolerate known multi-hop paths.

### Step 3: Evaluate the audit checks

Evaluate each check defined in `references/audit-checks.md`. The core checks are:

| Check | Severity |
|---|---|
| Redirect loop | High |
| Redirect chain ends in a 4xx/5xx/error | High |
| Chain exceeds the hop limit (likely a loop) | High |
| Chain longer than allowed (> max-chain hops) | High |
| HTTPS → HTTP downgrade in the chain | High |
| Temporary (302/303/307) redirect for a permanent move | Medium |
| Meta-refresh or JavaScript redirect instead of a 301 | Medium |
| Mixed permanent and temporary codes in one chain | Medium |
| Canonical points at a redirecting URL | Medium |
| Redirect silently drops the query string | Low |
| Final page's canonical differs from its own URL | Low |

### Step 4: Produce the report

Write a report following the structure in `references/report-template.md`:

1. **Summary** — URLs checked, how many redirect, hop-count distribution, issue counts by severity
2. **Hop distribution** — how many URLs resolve in 0/1/2/3+ hops
3. **Issues** — one section per failing check, listing the source URL, the full hop-by-hop chain, and the fix
4. **Prioritized action list** — ordered by severity and traffic impact

### Step 5: Recommend fixes

For each issue, give a concrete fix:

- **Chains:** collapse every multi-hop chain to a single 301 from the original URL straight to the final destination. Show the exact rewrite (e.g., `A → B → C` becomes `A → C`).
- **Loops:** identify the two rules fighting each other (commonly a trailing-slash rule plus a lowercase rule, or a www rule plus an HTTPS rule) and state which to change.
- **Redirects to errors:** repoint the redirect to a live, relevant page (not the homepage unless nothing better exists).
- **Temporary redirects:** change 302/307 to 301/308 for moves intended to be permanent; keep 302/307 only for genuinely temporary cases (A/B tests, geo, maintenance).
- **Meta/JS redirects:** replace with a server-side 301.
- Never invent the destination — base every recommended target on the final URL the chain already reaches or on the user's migration map.

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
- `scripts/collect_redirects.py` — resolve the full redirect chain for a crawl, sitemap, or URL list
- `scripts/audit_redirects.py` — run audit checks against a redirect inventory JSON file
