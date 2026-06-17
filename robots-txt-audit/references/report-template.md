# Robots.txt Audit Report Template

Use this structure for the final report delivered to the user.

```markdown
# Robots.txt Audit — {site}

**Date:** {date}
**Fetch:** {status} {content_type} | **Groups:** {n} | **Sitemaps declared:** {n}

## Summary

| Severity | Issues |
|---|---|
| High | {n} |
| Medium | {n} |
| Low | {n} |

{2–3 sentence overview of robots.txt health and the biggest wins. Lead with any
sitewide block, 5xx, redirect, or HTML-served file — those are emergencies.}

## Fetch & file

| Property | Value |
|---|---|
| URL | https://example.com/robots.txt |
| Status | 200 |
| Content-Type | text/plain |
| Size | 1.2 KB |
| Redirected | no |
| Served as HTML | no |
| BOM | no |

## High-severity issues

### Sitewide / availability problems ({n})

{Call out Disallow: / , 5xx, redirect, or HTML-served file with the exact agent
or line, and the fix. These can deindex the whole site.}

### Syntax errors ({n})

| Line | Text | Problem | Fix |
|---|---|---|---|
| 4 | Disallow /admin | missing colon | Use `Disallow: /admin` |

### File size ({n})

{Note if robots.txt exceeds 500 KiB and how to trim it.}

## Medium-severity issues

### Blocked render resources ({n})

| Resource | Type | Blocking rule | Fix |
|---|---|---|---|
| /assets/app.css | css | Disallow: /assets | Allow: /assets/ for CSS/JS |

### Sitemap directives ({n})

| Issue | Detail | Fix |
|---|---|---|
| No Sitemap: line | — | Add `Sitemap: https://example.com/sitemap.xml` |
| Unreachable sitemap | https://… → 404 | Fix the sitemap or update the URL |

### Other ({n})

{One row per failing check: no User-agent: * group, unsupported directives
(noindex/nofollow/crawl-delay), etc. Same style: problem, detail, fix.}

## Low-severity issues

{Brief list: 404 (allow-all), duplicate * group, BOM, empty Disallow alongside
real rules.}

## Current robots.txt

\`\`\`
{paste the file, or the relevant excerpt, so the user can see what changes against what}
\`\`\`

## Prioritized action list

1. {Highest-impact fix, with the exact line to add/remove/change}
2. ...
```

## Guidance

- Lead with availability and sitewide blocks: a `Disallow: /`, a 5xx, a redirect, or an HTML-served file can take a whole site out of search and dwarf every other finding.
- Reinforce the crawl-vs-index distinction in the summary: robots.txt blocks crawling, not indexing; use `noindex` (meta/header) on crawlable pages to remove a page from the index.
- Every issue row must quote the exact directive or line and give a concrete action ("remove `Disallow: /`", "add `Allow: /assets/`", "add `Sitemap: https://…`").
- Show the current file (or the relevant excerpt) so recommended edits are unambiguous.
- For unsupported directives, name the supported alternative (meta robots / X-Robots-Tag for noindex; Search Console for crawl rate).
- Order the action list by severity first, then by blast radius (how much of the site each fix unblocks).
