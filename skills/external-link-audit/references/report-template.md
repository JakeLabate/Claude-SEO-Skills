# External Link Audit Report Template

Use this structure for the final report delivered to the user.

```markdown
# External Link Audit — {site}

**Date:** {date}
**Scope:** {scope description}
**Pages crawled:** {n} | **External links analyzed:** {n} | **Unique domains:** {n}

## Summary

| Severity | Issues |
|---|---|
| High | {n} |
| Medium | {n} |
| Low | {n} |

{2–3 sentence overview of the site's outbound link health and the biggest wins.}

## Domain overview

| Domain | Links | Followed | Nofollow/Sponsored/UGC | Notes |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |

## High-severity issues

### Broken external links ({n})

| Source page | Broken target | Anchor text | Status | Suggested fix |
|---|---|---|---|---|
| ... | ... | ... | 404 | Replace with {live or archived URL} / remove |

### Affiliate/paid links missing rel="sponsored" ({n})

| Source page | Target | Anchor text | Current rel | Suggested fix |
|---|---|---|---|---|
| ... | ... | ... | (none) | Add rel="sponsored" |

## Medium-severity issues

{One subsection per failing check, same table style: affected pages, details, specific fix.}

## Low-severity issues

{Brief list or table.}

## Prioritized action list

1. {Highest-impact fix, with exact pages/links}
2. ...
```

## Guidance

- Every issue row must name the exact source URL, target URL, and a concrete fix — never generic advice.
- Cap tables at ~20 rows in the report body; attach or offer the full list (CSV/JSON) if larger.
- Order the action list by severity first, then by estimated user/equity impact (sitewide and high-traffic pages first).
- In the domain overview, sort by link count descending and flag any domain the user may not have intended to link.
