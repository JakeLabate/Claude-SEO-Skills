# Meta Data Audit Report Template

Use this structure for the final report delivered to the user.

```markdown
# Meta Data Audit — {site}

**Date:** {date}
**Scope:** {scope description}
**Pages crawled:** {n} | **Titles found:** {n} | **Meta descriptions found:** {n}

## Summary

| Severity | Issues |
|---|---|
| High | {n} |
| Medium | {n} |
| Low | {n} |

{2–3 sentence overview of the site's metadata health and the biggest wins.}

## Length distribution

| Band | Titles | Descriptions |
|---|---|---|
| Missing | {n} | {n} |
| Too short (< 30 / < 70 chars) | {n} | {n} |
| Good (30–60 / 70–160 chars) | {n} | {n} |
| Too long (> 60 / > 160 chars) | {n} | {n} |

## High-severity issues

### Missing titles ({n})

| Page | Suggested title |
|---|---|
| ... | ... |

### Missing meta descriptions ({n})

| Page | Suggested description |
|---|---|
| ... | ... |

### Duplicate titles ({n} groups)

| Shared title | Pages | Suggested differentiation |
|---|---|---|
| ... | {url1}, {url2}, ... | ... |

### Duplicate meta descriptions ({n} groups)

| Shared description | Pages | Suggested differentiation |
|---|---|---|
| ... | ... | ... |

## Medium-severity issues

{One subsection per failing check, same table style: page, current value, character count, suggested rewrite.}

## Low-severity issues

{Brief list or table.}

## Prioritized action list

1. {Highest-impact fix, with exact pages and ready-to-paste replacement values}
2. ...
```

## Guidance

- Every issue row must name the exact page URL, the current value, and a concrete replacement — never generic advice.
- Suggested titles must be near 60 characters and suggested descriptions near 155; state the character count when proposing values.
- Base every suggested value on the page's actual content (use the H1 and visible copy from the inventory); never invent facts, prices, or claims. If a page lacks enough information to write accurate metadata, say so instead of guessing.
- Cap tables at ~20 rows in the report body; attach or offer the full list (CSV/JSON) if larger.
- Group templated issues (e.g., every product page sharing one description) as a single template-level fix with a few example URLs.
- Order the action list by severity first, then by estimated traffic impact (high-traffic and high-intent pages first).
