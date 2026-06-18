# Sitemap Audit Report Template

Use this structure for the final report delivered to the user.

```markdown
# Sitemap Audit — {site}

**Date:** {date}
**Sitemaps found:** {n} | **URLs listed:** {n} | **URLs probed:** {n}

## Summary

| Severity | Issues |
|---|---|
| High | {n} |
| Medium | {n} |
| Low | {n} |

{2–3 sentence overview of sitemap health and the biggest wins.}

## Sitemap files

| Sitemap | Type | URLs | Size | Gzip | Error |
|---|---|---|---|---|---|
| /sitemap.xml | urlset | 1,240 | 210 KB | no | — |
| ... | ... | ... | ... | ... | ... |

## High-severity issues

### URLs returning errors ({n})

| URL | Status | Action |
|---|---|---|
| ... | 404 | Remove from sitemap |

### Redirecting URLs ({n})

| URL | Status | Final URL | Action |
|---|---|---|---|
| ... | 301 | ... | Replace with final URL |

### Noindex URLs ({n})

| URL | Source | Action |
|---|---|---|
| ... | meta robots / X-Robots-Tag | Remove from sitemap or remove noindex |

### Robots-blocked URLs ({n})

| URL | Action |
|---|---|
| ... | Unblock in robots.txt or remove from sitemap |

### Sitemap size / structure ({n})

{Note any sitemap over 50,000 URLs or 50MB, plus parse/fetch errors, with the fix.}

## Medium-severity issues

{One subsection per failing check: canonicalized-away URLs, wrong host/protocol, sitemaps not in robots.txt. Same table style: URL, problem, fix.}

## Low-severity issues

{Brief tables: duplicate URLs, lastmod problems, invalid priority/changefreq.}

## Prioritized action list

1. {Highest-impact fix, with exact URLs or the rule to change}
2. ...
```

## Guidance

- Every issue row must name the exact URL and the concrete action ("remove from sitemap", "replace with {final URL}", "unblock {path} in robots.txt").
- Reinforce the core rule in the summary: sitemaps should list only final, canonical, indexable 200 URLs.
- Group templated problems (e.g., an entire `/tag/` section that is noindexed but listed) into one fix with a few example URLs and the count.
- Cap tables at ~20 rows in the report body; attach or offer the full list (CSV/JSON) if larger.
- For lastmod, recommend dropping rather than faking it when accurate values cannot be maintained; note that Google ignores priority and changefreq.
- Order the action list by severity first, then by how many URLs each fix cleans up.
