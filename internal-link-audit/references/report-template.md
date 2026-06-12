# Internal Link Audit Report Template

Use this structure for the final report delivered to the user.

```markdown
# Internal Link Audit — {site}

**Date:** {date}
**Scope:** {scope description}
**Pages crawled:** {n} | **Internal links analyzed:** {n}

## Summary

| Severity | Issues |
|---|---|
| High | {n} |
| Medium | {n} |
| Low | {n} |

{2–3 sentence overview of the site's internal linking health and the biggest wins.}

## High-severity issues

### Broken internal links ({n})

| Source page | Broken target | Anchor text | Status | Suggested fix |
|---|---|---|---|---|
| ... | ... | ... | 404 | ... |

### Orphan pages ({n})

| Orphan page | Suggested linking pages | Suggested anchor text |
|---|---|---|
| ... | ... | ... |

## Medium-severity issues

{One subsection per failing check, same table style: affected pages, details, specific fix.}

## Low-severity issues

{Brief list or table.}

## Opportunities

{Pages that would benefit from more internal links, with suggested source pages and anchor text.}

## Prioritized action list

1. {Highest-impact fix, with exact pages/links}
2. ...
```

## Guidance

- Every issue row must name the exact source URL, target URL, and a concrete fix — never generic advice.
- Cap tables at ~20 rows in the report body; attach or offer the full list (CSV/JSON) if larger.
- Order the action list by severity first, then by estimated traffic/equity impact.
