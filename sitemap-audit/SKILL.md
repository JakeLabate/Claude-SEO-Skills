---
name: sitemap-audit
description: Audit a website's XML sitemaps for SEO. Discovers sitemaps from robots.txt, follows sitemap index files, and validates every listed URL to find broken (non-200) URLs, redirecting URLs, noindexed or robots-blocked URLs, URLs canonicalized to a different page, wrong-host or wrong-protocol URLs, duplicate URLs, oversized sitemaps (over 50,000 URLs or 50MB), parse errors, and missing or invalid lastmod/priority/changefreq values. Use when the user asks to audit, analyze, check, validate, or fix an XML sitemap, sitemap index, sitemap.xml, or sitemap coverage of a website.
---

# Sitemap Audit

Audit a website's XML sitemaps and produce an actionable SEO report.

## When to use this skill

Use this skill when the user asks to:

- Audit, validate, or check an XML sitemap or sitemap index
- Find sitemap URLs that 404, redirect, are noindexed, or are blocked by robots.txt
- Find URLs in the sitemap that canonicalize elsewhere or sit on the wrong host/protocol
- Check that sitemaps are declared in robots.txt and stay under the 50,000-URL / 50MB limits
- Clean up lastmod, priority, and changefreq metadata
- Improve the quality and trustworthiness of the URL set submitted to search engines

## Inputs to collect

Before starting, confirm with the user:

1. **Site URL or sitemap URL** — a live site root (e.g., `https://example.com`, which auto-discovers sitemaps via robots.txt and common paths) or a specific sitemap URL (`--sitemap`).
2. **Scope** — how many listed URLs to probe (default 2000). Large sitemaps can be sampled with `--max-urls`.
3. **Probing** — whether to fetch each listed URL to check status/canonical/noindex (default on). Use `--no-probe` for a fast structural-only pass (parse errors, size limits, lastmod hygiene).

> **Note on the indexable contract:** every URL in an XML sitemap should be a final, canonical, indexable `200` page. A URL that redirects, 404s, is noindexed, is blocked by robots.txt, or canonicalizes elsewhere does not belong in the sitemap. Most checks here enforce that contract.

## Workflow

### Step 1: Discover, parse, and probe the sitemaps

Use `scripts/collect_sitemap.py`:

```bash
python3 scripts/collect_sitemap.py https://example.com --max-urls 2000 --output sitemap_inventory.json
```

Point directly at a sitemap with `--sitemap`:

```bash
python3 scripts/collect_sitemap.py https://example.com/sitemap_index.xml --sitemap --output sitemap_inventory.json
```

The script reads `robots.txt` for `Sitemap:` directives (falling back to `/sitemap.xml` and `/sitemap_index.xml`), follows sitemap index files, handles gzipped sitemaps, and records each sitemap's type, URL count, byte size, and any parse/fetch error. For every listed URL it captures the sitemap's `lastmod`/`changefreq`/`priority`, then probes the URL for status, redirect target, `rel=canonical`, meta robots, the `X-Robots-Tag` header, and whether robots.txt disallows it.

### Step 2: Run the audit checks

Use `scripts/audit_sitemap.py`:

```bash
python3 scripts/audit_sitemap.py sitemap_inventory.json --output audit_report.json
```

### Step 3: Evaluate the audit checks

Evaluate each check defined in `references/audit-checks.md`. The core checks are:

| Check | Severity |
|---|---|
| No parseable sitemap found | High |
| Sitemap parse error / fetch error | High |
| Sitemap exceeds 50,000 URLs | High |
| Sitemap exceeds 50MB uncompressed | High |
| Listed URL returns 4xx/5xx/error | High |
| Listed URL redirects (not a final 200) | High |
| Listed URL is noindex (meta robots or X-Robots-Tag) | High |
| Listed URL is blocked by robots.txt | High |
| Listed URL canonicalizes to a different URL | Medium |
| Listed URL is on the wrong host or protocol | Medium |
| Sitemaps not declared in robots.txt | Medium |
| Duplicate URL across sitemaps | Low |
| Missing / invalid / future lastmod | Low |
| Invalid priority or changefreq | Low |

### Step 4: Produce the report

Write a report following the structure in `references/report-template.md`:

1. **Summary** — sitemaps found, total URLs listed, URLs probed, issue counts by severity
2. **Sitemap files** — table of each sitemap: type, URL count, size, gzip, errors
3. **Issues** — one section per failing check, listing the URL, the problem, and the fix
4. **Prioritized action list** — ordered by severity and impact

### Step 5: Recommend fixes

For each issue, give a concrete fix:

- **Non-200, redirecting, noindex, robots-blocked, or canonicalized URLs:** remove them from the sitemap (or, for redirects, replace each with its final destination URL). The sitemap should list only final indexable pages.
- **Wrong host/protocol:** rewrite URLs to the canonical host and `https://`.
- **Size limits:** split the sitemap into multiple files under 50,000 URLs / 50MB and reference them from a sitemap index.
- **Not in robots.txt:** add a `Sitemap:` line to robots.txt for each sitemap (or the index).
- **lastmod hygiene:** emit a valid W3C datetime reflecting the real last-modified date; drop `priority`/`changefreq` if they are arbitrary (Google ignores them).
- Base every recommendation on the observed data; do not invent URLs.

## Resources

- `references/audit-checks.md` — full definitions, thresholds, and rationale for every audit check
- `references/report-template.md` — report output structure
- `scripts/collect_sitemap.py` — discover, parse, and probe a site's XML sitemaps
- `scripts/audit_sitemap.py` — run audit checks against a sitemap inventory JSON file
