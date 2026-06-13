# Site Architecture Audit Report Template

Use this structure for the final report delivered to the user.

```markdown
# Site Architecture Audit : {site}

**Date:** {date}
**Scope:** {scope description}
**Pages crawled:** {n} | **Canonical host:** {host} | **robots.txt:** {found/missing} | **Sitemap URLs:** {n}

## Summary

| Severity | Issues |
|---|---|
| High | {n} |
| Medium | {n} |
| Low | {n} |

{2-3 sentence overview of the site's architectural health and the biggest wins.}

## Canonicalization and crawl controls

### Hostname / protocol variants

| Variant | Status | Resolves to | Canonical? |
|---|---|---|---|
| http://example.com | 301 | https://example.com/ | redirects (good) |
| https://www.example.com | 200 | https://www.example.com/ | duplicate (fix) |
| ... | ... | ... | ... |

### robots.txt

{Status, the Disallow rules that block indexable content, and whether a sitemap is declared.}

### Index-signal conflicts ({n})

| Page | Conflict | Suggested fix |
|---|---|---|
| ... | noindex + canonical to other URL | ... |

## URL and depth structure

### Click-depth distribution

| Depth | Pages |
|---|---|
| 0 | 1 |
| 1 | {n} |
| 2 | {n} |
| 3 | {n} |
| 4+ | {n} |

### URL-quality issues ({n})

| Page | Problem | Suggested URL |
|---|---|---|
| /Services/SEO_Audit | uppercase, underscore | /services/seo-audit |

### Directory map

| Section (first path segment) | Pages | Note |
|---|---|---|
| /blog | {n} | |
| /services | {n} | |
| /x | 1 | single-page section, consider consolidating |

## Sitemap health

### Non-indexable URLs in sitemap ({n})

| Sitemap URL | Problem | Suggested fix |
|---|---|---|
| ... | 301 redirect | list the final URL instead |

### Indexable pages missing from sitemap ({n})

| Page | Note |
|---|---|
| ... | add to sitemap |

## Prioritized action list

1. {Highest-impact fix, with exact hosts/URLs/rules}
2. ...
```

## Guidance

- Every issue row must name the exact URL or rule and a concrete fix, never generic advice.
- Lead the action list with canonicalization and robots.txt issues: a single host-redirect or one over-broad `Disallow` line usually outweighs dozens of cosmetic URL fixes.
- Cap tables at ~20 rows in the report body; attach or offer the full list (CSV/JSON) if larger.
- Group templated problems (every product URL using underscores, a whole section missing from the sitemap) as one template-level fix with a few example URLs rather than listing hundreds of rows.
- When recommending URL changes, always pair them with a 301 from the old URL so existing equity and links are preserved.
- State thresholds you used (click-depth and URL-depth limits) so the user can recalibrate for their site type.
