<!-- Illustrative sample output for the sitemap-audit skill. Fictional data. -->

# Sitemap Audit — example.com

**Date:** 2026-06-18
**Scope:** Discovered via `robots.txt`; followed the sitemap index; probed 1,204 listed URLs.

## Summary

| Severity | Issues |
|---|---|
| High | 63 |
| Medium | 41 |
| Low | 12 |

The sitemap index is healthy and declared in `robots.txt`, but ~9% of listed
URLs violate the indexable contract: 38 redirect (the site migrated to `https://`
and the sitemap still lists `http://`), 19 return 404, and 6 are noindexed. The
single highest-impact fix is regenerating the sitemap from canonical `https://`
URLs.

## Sitemap files

| Sitemap | Type | URLs | Size | Gzip | Errors |
|---|---|---|---|---|---|
| `/sitemap_index.xml` | index | 3 children | 0.4 KB | no | — |
| `/sitemap-pages.xml` | urlset | 204 | 38 KB | no | — |
| `/sitemap-products.xml` | urlset | 612 | 110 KB | no | — |
| `/sitemap-blog.xml` | urlset | 388 | 71 KB | no | — |

## High-severity issues

### Listed URLs that redirect (38)

All are `http://` URLs that 301 to their `https://` equivalent.

| Listed URL | Resolves to | Fix |
|---|---|---|
| `http://example.com/products/widget-a/` | `https://example.com/products/widget-a/` (301) | List the `https://` URL directly |
| … 37 more | | Regenerate the sitemap from canonical URLs |

### Listed URLs returning 4xx/5xx (19)

| Listed URL | Status | Fix |
|---|---|---|
| `https://example.com/products/discontinued-gadget/` | 404 | Remove from sitemap (or restore the page) |
| `https://example.com/blog/old-post/` | 410 | Remove from sitemap |
| … 17 more | | |

### Noindexed URLs in the sitemap (6)

| Listed URL | Signal | Fix |
|---|---|---|
| `https://example.com/account/settings/` | `<meta robots noindex>` | Remove from sitemap — noindex pages don't belong |
| … 5 more | `X-Robots-Tag: noindex` | |

## Medium-severity issues

### URLs canonicalizing elsewhere (29)

Faceted product URLs (`?color=`) list in the sitemap but canonicalize to the base
product. Submit only the canonical URL.

### Wrong host/protocol (12)

12 URLs use the `www.` host while the site canonicalizes to the bare domain.

## Low-severity issues

- **Missing `lastmod` (8)** on `/sitemap-pages.xml` entries.
- **Future `lastmod` (3)** dated 2027 — likely a timezone/serialization bug.
- **Arbitrary `priority` (all 612 product URLs set to `1.0`)** — Google ignores
  it; consider dropping the field.

## Prioritized action list

1. **Regenerate the sitemap from canonical `https://` (bare-host) URLs** (high).
   Fixes the 38 redirects and 12 wrong-host entries in one change.
2. **Remove the 19 dead URLs and 6 noindexed URLs** (high). The sitemap should
   list only final, indexable `200` pages.
3. **Drop faceted `?color=` URLs; list only canonicals** (medium, 29 URLs).
4. **Add real `lastmod` values and remove the blanket `priority: 1.0`** (low).

> Every listed URL and its probe result is in `sitemap_inventory.json`; findings
> grouped by check are in `audit_report.json`.
