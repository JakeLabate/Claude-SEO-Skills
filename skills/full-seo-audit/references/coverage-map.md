# Coverage map

What each sub-skill audits, the scripts it runs, and what it needs as input. Use
this to decide which skills are in scope for a given request and to map a user's
words ("indexation", "page speed", "international") to the right skills.

## Crawlability & indexation

| Skill | Finds | Needs |
|---|---|---|
| `robots-txt-audit` | Sitewide `Disallow: /`, syntax errors, blocked CSS/JS, missing/unreachable `Sitemap:`, unsupported directives | robots.txt |
| `sitemap-audit` | Dead/redirecting/noindexed/blocked URLs in sitemaps, size limits, lastmod hygiene | sitemap(s) |
| `site-architecture-audit` | Host/protocol canonicalization, sitemap parity, crawl/index conflicts, click depth, URL quality | site + robots + sitemap |
| `redirect-audit` | Redirect chains/loops, 302-for-permanent, HTTPS→HTTP, meta/JS redirects, dropped query strings | URL list or crawl |
| `soft-404-audit` | Pages that return 200 but are really "not found" / empty | crawl |

## Links

| Skill | Finds | Needs |
|---|---|---|
| `internal-link-audit` | Broken links, orphans, redirect chains, click depth, anchor quality, equity distribution | crawl |
| `external-link-audit` | Broken/redirected outbound links, insecure HTTP, `rel="sponsored"` compliance, unsafe `target="_blank"` | crawl |
| `pagination-audit` | `rel=next/prev`, canonical-on-paginated mistakes, orphaned/duplicated paginated pages | crawl |

## On-page & indexation signals

| Skill | Finds | Needs |
|---|---|---|
| `meta-data-audit` | Missing/duplicate/long/short/generic titles & descriptions, stuffing | crawl |
| `heading-structure-audit` | Missing/multiple H1s, skipped levels, empty/long/duplicate headings | crawl |
| `canonical-tag-audit` | Missing/duplicate/relative canonicals, canonical to non-200/redirect/noindex, cross-host, self vs. cluster | crawl |
| `schema-markup-audit` | Missing/invalid/incomplete JSON-LD, Microdata, RDFa vs. Google requirements | crawl |
| `open-graph-audit` | Missing/duplicate OG & Twitter Card tags, bad image dimensions, og:url mismatches | crawl |

## Content

| Skill | Finds | Needs |
|---|---|---|
| `content-quality-audit` | Thin content, low text-to-HTML, duplicate/near-duplicate bodies, missing main content | crawl |
| `keyword-cannibalization-audit` | Multiple pages targeting the same query via title/H1/overlap | crawl |

## Security & delivery

| Skill | Finds | Needs |
|---|---|---|
| `mixed-content-audit` | HTTP subresources on HTTPS pages, insecure form actions, upgradeable links | crawl |
| `core-web-vitals-audit` | LCP/CLS/INP/TTFB field data (with API key) + lab proxies | per-URL; optional PSI key |

## AI discoverability

| Skill | Finds | Needs |
|---|---|---|
| `llms-txt-audit` | Missing/malformed `/llms.txt`, broken links, missing descriptions | /llms.txt |

## Sharing one crawl

Most on-page skills crawl HTML. To avoid hammering the site, prefer running the
broadest crawler first (e.g. `site-architecture-audit` or `internal-link-audit`)
and feeding the discovered URL set to the others via their `--url-list` mode
where supported, or cap `--max-pages` consistently across skills.
